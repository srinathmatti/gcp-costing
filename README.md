# GCP-Costing-AI 🚀

Local dashboard for GKE cluster cost analysis with exact billing and real-time metrics.

## ✨ Features

- 🔐 **ADC Authentication** - No service accounts needed, uses `gcloud auth application-default login`
- 💰 **Exact Billing** - Real pricing from Cloud Billing API `services.skus.list` [[6]]
- 📊 **Real Metrics** - CPU/memory from `kubernetes.io/container/cpu/core_usage_time` [[12]]
- 🌐 **Network Monitoring** - `compute.googleapis.com/instance/network/received_bytes`
- 🎯 **Drill-down UI** - Project → Region → Cluster → NodePool → Node → Pods

## 🚀 Quick Start

```bash
# Prerequisites
# - Docker & Docker Compose
# - gcloud CLI installed and authenticated

# 1. Authenticate for ADC
gcloud auth application-default login

# 2. Enable APIs
gcloud services enable container.googleapis.com compute.googleapis.com monitoring.googleapis.com cloudbilling.googleapis.com

# 3. Get cluster credentials
gcloud container clusters get-credentials CLUSTER_NAME --region REGION --project PROJECT_ID

# 4. Run locally
docker compose up --build

# 5. Open http://localhost:5173



┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   GCP APIs      │
│   (React/Vite)  │◀────│   (FastAPI)     │◀────│   - Billing     │
│   Port 5173     │     │   Port 8000     │     │   - Monitoring  │
└─────────────────┘     └─────────────────┘     │   - Container   │
                           │                    │   - Compute     │
                           ▼                    └─────────────────┘
                    ┌───────────────────────┐
                    │   Local Auth          │
                    │   - ~/.config/gcloud  │
                    │   - ~/.kube/config    │
                    └───────────────────────┘



# Backend only (for debugging)
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend only
cd frontend
npm install
npm run dev



# 1. Stop containers
docker compose down

# 2. Clear build cache (important!)
docker builder prune -f

# 3. Rebuild and start
docker compose up --build

# 4. Check logs
docker compose logs -f backend