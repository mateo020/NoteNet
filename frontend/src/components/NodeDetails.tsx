import React, { useEffect, useState } from 'react';
import './NodeDetails.css';

interface NodeDetailsProps {
  node: {
    id: string;
    label: string;
  };
  onClose: () => void;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ node, onClose }) => {
  const [context, setContext] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContext = async () => {
      if (!node) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`http://localhost:8000/api/node_context/${encodeURIComponent(node.label)}`);
        if (!response.ok) {
          throw new Error('Failed to fetch context');
        }
        const data = await response.json();
        setContext(data.context);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch context');
      } finally {
        setLoading(false);
      }
    };

    fetchContext();
  }, [node]);

  if (!node) return null;

  return (
    <div className="node-details">
      <button className="close-button" onClick={onClose}>×</button>
      <div className="details-content">
        <h3>Node Details</h3>
        <p><strong>ID:</strong> {node.id}</p>
        <p><strong>Label:</strong> {node.label}</p>
        
        <div className="context-section">
          <h4>Context</h4>
          {loading && <p className="loading">Loading context...</p>}
          {error && <p className="error">{error}</p>}
          {!loading && !error && (
            <div className="context-content">
              {context.split('\n\n').map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}; 