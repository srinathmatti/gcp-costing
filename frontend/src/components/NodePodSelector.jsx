import React, { useState } from 'react';

export default function NodePodSelector({ nodes, pods, onNodesSelected, onLoadPods }) {
  const [selectedNodes, setSelectedNodes] = useState([]);

  const toggleNode = (node) => {
    setSelectedNodes(prev => 
      prev.find(n => n.name === node.name)
        ? prev.filter(n => n.name !== node.name)
        : [...prev, node]
    );
  };

  const handleLoadPods = () => {
    onNodesSelected(selectedNodes);
    onLoadPods(selectedNodes);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-semibold mb-3">Select Nodes (Multi-select)</h3>
        <div className="flex flex-wrap gap-2">
          {nodes.map(node => (
            <label 
              key={node.name}
              className={`px-3 py-2 border rounded cursor-pointer transition ${
                selectedNodes.find(n => n.name === node.name)
                  ? 'bg-green-100 border-green-500 text-green-800'
                  : 'hover:bg-gray-50'
              }`}
            >
              <input
                type="checkbox"
                className="mr-2"
                checked={!!selectedNodes.find(n => n.name === node.name)}
                onChange={() => toggleNode(node)}
              />
              {node.name}
              <span className="text-xs text-gray-500 ml-1">({node.status})</span>
            </label>
          ))}
        </div>
      </div>

      {selectedNodes.length > 0 && (
        <button
          onClick={handleLoadPods}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition"
        >
          Load Pods for {selectedNodes.length} Node(s)
        </button>
      )}

      {pods.length > 0 && (
        <div className="mt-6">
          <h3 className="font-semibold mb-3">Pods on Selected Nodes</h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="p-2 text-left border">Pod</th>
                  <th className="p-2 text-left border">Namespace</th>
                  <th className="p-2 text-left border">Status</th>
                  <th className="p-2 text-left border">Node</th>
                  <th className="p-2 text-right border">CPU Request</th>
                  <th className="p-2 text-right border">Memory Request</th>
                </tr>
              </thead>
              <tbody>
                {pods.map(pod => (
                  <tr key={`${pod.namespace}/${pod.name}`} className="hover:bg-gray-50">
                    <td className="p-2 border font-medium">{pod.name}</td>
                    <td className="p-2 border">{pod.namespace}</td>
                    <td className="p-2 border">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        pod.status === 'Running' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {pod.status}
                      </span>
                    </td>
                    <td className="p-2 border">{pod.node}</td>
                    <td className="p-2 border text-right">{pod.cpu_request || '-'} cores</td>
                    <td className="p-2 border text-right">{pod.memory_request_gb?.toFixed(2) || '-'} GB</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}