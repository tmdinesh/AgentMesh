import React from 'react';
import { Sparkles, GitCommit, Network, Activity } from 'lucide-react';

export default function TopologyBadge({ topology }) {
  const norm = (topology || '').toUpperCase();

  if (norm === 'STAR') {
    return (
      <span className="badge badge-star">
        <Sparkles size={13} />
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

  if (norm === 'UNCONSTRAINED' || norm === 'EMERGENT') {
    return (
      <span className="badge badge-unconstrained">
        <Activity size={13} />
        Unconstrained / Emergent
      </span>
    );
  }

  return <span className="badge badge-secondary">{topology}</span>;
}
