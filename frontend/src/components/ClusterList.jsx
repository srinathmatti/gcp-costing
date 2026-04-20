import React from 'react';

export default function ClusterList({ clusters, onClusterClick }) {
  if (clusters.length === 0) {
    return <p className="text-gray-500">No clusters found.</p>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {clusters.map(cluster => (
        <div 
          key={cluster.name}
          onClick={() => onClusterClick(cluster)}
          className="border rounded-lg p-4 cursor-pointer hover:shadow-lg transition bg-white"
        >
          <div className="flex justify-between items-start">
            <h3 className="font-semibold text-lg">{cluster.name}</h3>
            <span className={`px-2 py-1 rounded text-xs ${
              cluster.status === 'RUNNING' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
            }`}>
              {cluster.status}
            </span>
          </div>
          
          <div className="mt-3 space-y-2 text-sm text-gray-600">
            <p>📍 {cluster.location}</p>
            <p>🔧 Node Pools: {cluster.node_pools_count}</p>
            <p>🖥️ Total Nodes: {cluster.total_nodes}</p>
            <p className="font-medium text-blue-600">
              💰 Est. Cost: ${cluster.approx_monthly_cost_usd}/month
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}