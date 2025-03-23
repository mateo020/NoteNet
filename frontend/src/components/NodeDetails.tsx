import React from 'react';
import './NodeDetails.css';

interface NodeDetailsProps {
  node: {
    id: string;
    label: string;
  } | null;
  onClose: () => void;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <div className="node-details">
      <button className="close-button" onClick={onClose}>×</button>
      <h3>Node Details</h3>
      <div className="details-content">
        <p><strong>ID:</strong> {node.id}</p>
        <p><strong>Label:</strong> {node.label}</p>
      </div>
    </div>
  );
}; 