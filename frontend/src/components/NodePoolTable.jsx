import React from 'react';

export default function NodePoolTable({ nodePools, onNodePoolClick }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-3 text-left border">Name</th>
            <th className="p-3 text-left border">Machine Type</th>
            <th className="p-3 text-center border">Nodes</th>
            <th className="p-3 text-left border">Zones</th>
            <th className="p-3 text-right border">Cost/Mo</th>
            <th className="p-3 text-center border">CPU%</th>
            <th className="p-3 text-center border">Mem%</th>
            <th className="p-3 text-center border">IP%</th>
            <th className="p-3 text-center border">Autoscale</th>
          </tr>
        </thead>
        <tbody>
          {nodePools.map(np => (
            <tr 
              key={np.name}
              onClick={() => onNodePoolClick(np)}
              className="cursor-pointer hover:bg-blue-50 transition"
            >
              <td className="p-3 border font-medium">{np.name}</td>
              <td className="p-3 border">{np.machine_type}</td>
              <td className="p-3 border text-center">{np.nodes}</td>
              <td className="p-3 border">{np.zones.join(', ')}</td>
              <td className="p-3 border text-right font-medium text-green-600">
                ${np.approx_monthly_cost_usd}
              </td>
              <td className="p-3 border text-center">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{width: `${np.cpu_usage_pct}%`}}></div>
                </div>
                <span className="text-xs">{np.cpu_usage_pct}%</span>
              </td>
              <td className="p-3 border text-center">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-purple-500 h-2 rounded-full" style={{width: `${np.memory_usage_pct}%`}}></div>
                </div>
                <span className="text-xs">{np.memory_usage_pct}%</span>
              </td>
              <td className="p-3 border text-center">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-orange-500 h-2 rounded-full" style={{width: `${np.ip_usage_pct}%`}}></div>
                </div>
                <span className="text-xs">{np.ip_usage_pct}%</span>
              </td>
              <td className="p-3 border text-center text-sm">
                {np.autoscale_min}-{np.autoscale_max}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}