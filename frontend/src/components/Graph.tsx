import React, { useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { NodeDetails } from './NodeDetails';
import './Graph.css';

interface Node {
  id: string;
  label: string;
}

interface Edge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export const Graph: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const [nodesResponse, edgesResponse] = await Promise.all([
          fetch('http://localhost:8000/api/latest_entities/nodes'),
          fetch('http://localhost:8000/api/latest_entities/relationships')
        ]);

        if (!nodesResponse.ok || !edgesResponse.ok) {
          throw new Error('Failed to fetch graph data');
        }

        const nodesData = await nodesResponse.json();
        const edgesData = await edgesResponse.json();

        setNodes(nodesData);
        setEdges(edgesData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    };

    fetchGraphData();
  }, []);

  const handleNodeClick = (node: Node) => {
    setSelectedNode(node);
  };

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  if (nodes.length === 0 || edges.length === 0) {
    return <div className="loading-message">Loading graph data...</div>;
  }

  return (
    <div className="graph-container">
      <div className="graph-wrapper">
        <ForceGraph2D
          graphData={{ nodes, links: edges }}
          nodeLabel="label"
          linkLabel="label"
          nodeColor="#007bff"
          linkColor="#666666"
          backgroundColor="#ffffff"
          width={800}
          height={600}
          nodeRelSize={6}
          linkWidth={2}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.004}
          onNodeClick={handleNodeClick}
        />
        {selectedNode && (
          <NodeDetails
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
      <div className="graph-legend">
        <p>Nodes: {nodes.length}</p>
        <p>Relationships: {edges.length}</p>
      </div>
    </div>
  );
}; 