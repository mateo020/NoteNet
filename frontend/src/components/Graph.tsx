import React, { useEffect, useState } from 'react';
// import ForceGraph2D from 'react-force-graph-2d';
import './Graph.css';

interface Entity {
    name: string;
    description: string;
}

interface GraphData {
    nodes: Array<{
        id: string;
        name: string;
        description: string;
        val: number;
    }>;
    links: Array<{
        source: string;
        target: string;
        value: number;
    }>;
}

const Graph: React.FC = () => {
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchEntities = async () => {
            try {
                // Get the latest entities file from the backend
                const response = await fetch('http://localhost:8000/api/latest_entities');
                if (!response.ok) {
                    throw new Error('Failed to fetch entities');
                }
                const entities: Record<string, string> = await response.json();
                
                // Transform entities into graph data
                const nodes = Object.entries(entities).map(([name, description], index) => ({
                    id: name,
                    name,
                    description,
                    val: 1 + Math.random() * 2, // Random size for visual variety
                }));

                // Create links between related entities
                const links = nodes.map((node, i) => ({
                    source: node.id,
                    target: nodes[(i + 1) % nodes.length].id, // Connect to next node
                    value: 1,
                }));

                setGraphData({ nodes, links });
            } catch (err) {
                setError(err instanceof Error ? err.message : 'An error occurred');
            } finally {
                setLoading(false);
            }
        };

        fetchEntities();
    }, []);

    if (loading) {
        return <div className="graph-container">Loading graph...</div>;
    }

    if (error) {
        return <div className="graph-container error">Error: {error}</div>;
    }

    return (
        <div className="graph-container">
            <h2>Entity Relationship Graph</h2>
            <div className="graph-wrapper">
                <ForceGraph2D
                    graphData={graphData}
                    nodeLabel="description"
                    nodeRelSize={6}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleSpeed={0.004}
                    backgroundColor="#ffffff"
                    width={800}
                    height={600}
                />
            </div>
            <div className="graph-legend">
                <h3>Entities</h3>
                <ul>
                    {graphData.nodes.map(node => (
                        <li key={node.id}>
                            <strong>{node.name}:</strong> {node.description}
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default Graph; 