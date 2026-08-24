import React from 'react';
import { Star, GitCommit, Network, Activity, GitBranch } from 'lucide-react';

export default function TopologyBadge({ topology }) {
  const norm = (topology || '').toUpperCase();

  if (norm === 'STAR') {
    return (
      <span className="badge badge-star">
        <Star size={13} fill="currentColor" fillOpacity={0.2} />
        Star
      </span>
    );
  }

  if (norm === 'CHAIN') {
    return (
      <span className="badge badge-chain">
        <GitCommit size={13} />
        Chain
      </span>
    );
  }

  if (norm === 'MESH') {
    return (
      <span className="badge badge-mesh">
        <Network size={13} />
        Mesh
      </span>
    );
  }

  if (norm === 'TREE') {
    return (
      <span className="badge" style={{ background: 'rgba(236, 72, 153, 0.15)', color: '#ec4899', border: '1px solid rgba(236, 72, 153, 0.4)' }}>
        <GitBranch size={13} />
        Tree
      </span>
    );
  }

  if (norm === 'UNCONSTRAINED' || norm === 'EMERGENT') {
    return (
      <span className="badge badge-unconstrained">
        <Activity size={13} />
        Emergent
      </span>
    );
  }

  return <span className="badge badge-secondary">{topology}</span>;
}
