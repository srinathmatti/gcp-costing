import React from 'react';

export default function RegionProjectSelector({ 
  regions, projects, selectedRegion, selectedProject, 
  onRegionChange, onProjectChange, onLoad 
}) {
  return (
    <div className="flex flex-wrap gap-4 p-4 bg-white rounded-lg shadow mb-6">
      <div className="flex-1 min-w-[200px]">
        <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
        <select 
          className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
          value={selectedRegion}
          onChange={(e) => onRegionChange(e.target.value)}
        >
          <option value="">Select Region</option>
          {regions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      
      <div className="flex-1 min-w-[200px]">
        <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
        <select 
          className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
          value={selectedProject}
          onChange={(e) => onProjectChange(e.target.value)}
        >
          <option value="">Select Project</option>
          {projects.map(p => <option key={p.project_id} value={p.project_id}>{p.name}</option>)}
        </select>
      </div>
      
      <div className="flex items-end">
        <button 
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition disabled:opacity-50"
          onClick={onLoad}
          disabled={!selectedRegion || !selectedProject}
        >
          Load Clusters
        </button>
      </div>
    </div>
  );
}