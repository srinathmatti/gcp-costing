import React, { useState, useEffect } from 'react';
import RegionProjectSelector from './components/RegionProjectSelector';
import ClusterList from './components/ClusterList';
import NodePoolTable from './components/NodePoolTable';
import NodePodSelector from './components/NodePodSelector';

const API_BASE = 'http://localhost:8000/api';

export default function App() {
  const [regions, setRegions] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedProject, setSelectedProject] = useState('');
  
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  
  const [nodePools, setNodePools] = useState([]);
  const [selectedNodePool, setSelectedNodePool] = useState(null);
  
  const [nodes, setNodes] = useState([]);
  const [pods, setPods] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [regionsRes, projectsRes] = await Promise.all([
          fetch(`${API_BASE}/regions`),
          fetch(`${API_BASE}/projects`)
        ]);
        setRegions(await regionsRes.json());
        setProjects(await projectsRes.json());
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    };
    fetchData();
  }, []);

  const loadClusters = async () => {
    if (!selectedRegion || !selectedProject) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/clusters?project=${selectedProject}&region=${selectedRegion}`
      );
      setClusters(await res.json());
    } catch (err) {
      console.error('Failed to load clusters:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadNodePools = async (cluster) => {
    setSelectedCluster(cluster);
    setSelectedNodePool(null);
    setNodes([]);
    setPods([]);
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/clusters/${cluster.name}/nodepools?project=${selectedProject}&region=${selectedRegion}`
      );
      setNodePools(await res.json());
    } catch (err) {
      console.error('Failed to load node pools:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadNodes = async (nodePool) => {
    setSelectedNodePool(nodePool);
    setNodes([]);
    setPods([]);
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/nodepools/${nodePool.name}/nodes?project=${selectedProject}&region=${selectedRegion}&cluster_name=${selectedCluster.name}`
      );
      setNodes(await res.json());
    } catch (err) {
      console.error('Failed to load nodes:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPods = async (selectedNodes) => {
    setLoading(true);
    try {
      const podPromises = selectedNodes.map(node =>
        fetch(
          `${API_BASE}/nodes/${node.name}/pods?project=${selectedProject}&region=${selectedRegion}&cluster_name=${selectedCluster.name}`
        ).then(res => res.json())
      );
      const allPods = (await Promise.all(podPromises)).flat();
      setPods(allPods);
    } catch (err) {
      console.error('Failed to load pods:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">🚀 GCP Costing AI</h1>
        <p className="text-gray-600">GKE Cluster Cost & Resource Dashboard</p>
      </header>

      <RegionProjectSelector
        regions={regions}
        projects={projects}
        selectedRegion={selectedRegion}
        selectedProject={selectedProject}
        onRegionChange={setSelectedRegion}
        onProjectChange={setSelectedProject}
        onLoad={loadClusters}
      />

      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {clusters.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">GKE Clusters</h2>
          <ClusterList clusters={clusters} onClusterClick={loadNodePools} />
        </section>
      )}

      {selectedCluster && nodePools.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">
            Node Pools: {selectedCluster.name}
          </h2>
          <NodePoolTable nodePools={nodePools} onNodePoolClick={loadNodes} />
        </section>
      )}

      {selectedNodePool && nodes.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">
            Nodes in {selectedNodePool.name}
          </h2>
          <NodePodSelector
            nodes={nodes}
            pods={pods}
            onNodesSelected={() => {}}
            onLoadPods={loadPods}
          />
        </section>
      )}
    </div>
  );
}