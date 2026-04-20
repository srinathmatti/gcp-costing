"""
Cloud Billing API integration for exact pricing.
Uses services.skus.list to fetch real SKU rates.
Reference: https://docs.cloud.google.com/billing/docs/how-to/get-pricing-information-api [[6]]
"""
from google.cloud import billing_v1
from google.auth import default
from google.api_core import exceptions
from typing import Optional, Dict, List
import re
from datetime import datetime, timedelta
import asyncio

class BillingService:
    def __init__(self, credentials=None, billing_account_id: Optional[str] = None):
        self.credentials = credentials or default()[0]
        self.billing_account_id = billing_account_id
        self.client = billing_v1.CloudBillingClient(credentials=self.credentials)
        self._sku_cache: Dict[str, dict] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._CACHE_TTL_HOURS = 6  # Cache SKU prices for 6 hours

    def _get_service_filter(self, service_name: str) -> str:
        """Map common service names to Cloud Billing service IDs."""
        service_map = {
            "compute": "services/6F81-5844-456A",  # Compute Engine
            "container": "services/39E3-0C18-7A68",  # GKE
            "networking": "services/9662-B51E-5089",  # Network
        }
        return service_map.get(service_name.lower(), "")

    def _parse_price_tier(self, pricing_info: dict, currency: str = "USD") -> float:
        """Extract hourly rate from pricing tiers."""
        if not pricing_info.get("tiers"):
            return 0.0
        
        # Get first tier (usually the base rate)
        tier = pricing_info["tiers"][0]
        list_price = tier.get("listPrice", {})
        
        if list_price.get("currencyCode") != currency:
            return 0.0
        
        # Convert nano units to standard units
        units = list_price.get("units", "0")
        nanos = list_price.get("nanos", 0)
        return float(units) + (nanos / 1e9)

    def _extract_unit_info(self, pricing_info: dict) -> tuple[str, float]:
        """Extract unit type and quantity from pricing info."""
        unit_info = pricing_info.get("unitInfo", {})
        unit = unit_info.get("unit", "h")  # Default to hour
        quantity = float(unit_info.get("unitQuantity", {}).get("value", "1"))
        return unit, quantity

    def _matches_machine_type(self, sku: dict, machine_type: str) -> bool:
        """Check if SKU matches the requested machine type."""
        display_name = sku.get("displayName", "").lower()
        machine_lower = machine_type.lower()
        
        # Extract base machine type (e.g., "e2-medium" from "e2-medium in us-central1")
        base_type = re.match(r'^([a-z0-9]+-[a-z0-9]+)', machine_lower)
        if not base_type:
            return False
        
        return base_type.group(1) in display_name

    def _matches_region(self, sku: dict, region: str) -> bool:
        """Check if SKU matches the requested region."""
        geo = sku.get("geoTaxonomy", {})
        if geo.get("type") == "REGIONAL":
            sku_region = geo.get("regionalMetadata", {}).get("region", {}).get("region", "")
            return region in sku_region
        return True  # Global SKU applies everywhere

    async def fetch_machine_price(self, machine_type: str, region: str, 
                                commitment: str = "OnDemand") -> Optional[float]:
        """
        Fetch exact hourly price for a machine type from Cloud Billing API.
        Uses caching to minimize API calls.
        """
        now = datetime.utcnow()
        
        # Check cache first
        if (self._cache_timestamp and 
            now - self._cache_timestamp < timedelta(hours=self._CACHE_TTL_HOURS) and
            machine_type in self._sku_cache):
            return self._sku_cache[machine_type].get("hourly_rate")
        
        try:
            # List SKUs for Compute Engine service
            service_filter = self._get_service_filter("compute")
            if not service_filter:
                return None
            
            # Build filter query
            filter_query = f'service="{service_filter}" AND category="GCE Instance"'
            if region:
                filter_query += f' AND region="regions/{region}"'
            
            # Fetch SKUs with pagination
            request = billing_v1.ListSkusRequest(
                parent="services/6F81-5844-456A",  # Compute Engine service
                filter=filter_query,
                currency_code="USD"
            )
            
            matching_sku = None
            for page in self.client.list_skus(request=request).pages:
                for sku in page.skus:
                    if (self._matches_machine_type(sku.to_dict(), machine_type) and 
                        self._matches_region(sku.to_dict(), region)):
                        # Check pricing info for OnDemand/Preemptible
                        for pricing in sku.pricing_info:
                            if commitment.lower() in str(pricing).lower() or commitment == "OnDemand":
                                matching_sku = sku.to_dict()
                                break
                    if matching_sku:
                        break
                if matching_sku:
                    break
            
            if not matching_sku:
                # Fallback: try without region filter
                request = billing_v1.ListSkusRequest(
                    parent="services/6F81-5844-456A",
                    filter=f'service="{service_filter}" AND category="GCE Instance"',
                    currency_code="USD"
                )
                for page in self.client.list_skus(request=request).pages:
                    for sku in page.skus:
                        if self._matches_machine_type(sku.to_dict(), machine_type):
                            matching_sku = sku.to_dict()
                            break
                    if matching_sku:
                        break
            
            if not matching_sku:
                return None
            
            # Parse pricing
            pricing_info = matching_sku["pricingInfo"][0] if matching_sku.get("pricingInfo") else {}
            hourly_rate = self._parse_price_tier(pricing_info)
            
            # Adjust for unit (e.g., if priced per GiB-hr, multiply by memory)
            unit, quantity = self._extract_unit_info(pricing_info)
            if "GiBy" in unit or "GB" in unit:
                # Extract memory from machine type (e.g., e2-standard-4 has 16GB)
                memory_gb = self._extract_memory_gb(machine_type)
                hourly_rate *= memory_gb
            
            # Cache result
            self._sku_cache[machine_type] = {
                "hourly_rate": hourly_rate,
                "sku_id": matching_sku.get("skuId"),
                "display_name": matching_sku.get("displayName")
            }
            self._cache_timestamp = now
            
            return hourly_rate
            
        except exceptions.GoogleAPIError as e:
            print(f"⚠️ Billing API error: {e}")
            return None

    def _extract_memory_gb(self, machine_type: str) -> float:
        """Extract memory in GB from machine type name."""
        # Common GCP machine type memory mappings
        memory_map = {
            "e2-micro": 1, "e2-small": 2, "e2-medium": 4,
            "e2-standard-2": 8, "e2-standard-4": 16, "e2-standard-8": 32,
            "n1-standard-1": 3.75, "n1-standard-2": 7.5, "n1-standard-4": 15,
            "n2-standard-2": 8, "n2-standard-4": 16,
            "c2-standard-4": 16, "c2-standard-8": 32,
        }
        return memory_map.get(machine_type, 4)  # Default to 4GB

    def calculate_monthly_cost(self, hourly_rate: float, node_count: int, 
                             hours_per_month: float = 730) -> float:
        """Calculate approximate monthly cost."""
        return round(hourly_rate * node_count * hours_per_month, 2)