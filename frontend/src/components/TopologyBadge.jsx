import React from 'react';
import { Star, GitCommit, Network, Activity, GitBranch, Boxes, Radio, Database } from 'lucide-react';

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

  if (norm === 'ACTOR') {
    return (
      <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.4)' }}>
        <Boxes size={13} />
        Actor (Ray)
      </span>
    );
  }

  if (norm === 'STREAM' || norm === 'KAFKA') {
    return (
      <span className="badge" style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: '1px solid rgba(244, 63, 94, 0.4)' }}>
        <Radio size={13} />
        Stream (Kafka)
      </span>
    );
  }

  if (norm === 'DISTRIBUTED_STATE' || norm === 'ETCD') {
    return (
      <span className="badge" style={{ background: 'rgba(20, 184, 166, 0.15)', color: '#2dd4bf', border: '1px solid rgba(20, 184, 166, 0.4)' }}>
        <Database size={13} />
        Distributed State
      </span>
    );
  }

  return <span className="badge badge-secondary">{topology}</span>;
}

