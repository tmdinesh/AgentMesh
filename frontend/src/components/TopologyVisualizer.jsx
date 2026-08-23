import React, { useState } from 'react';
import { UserCheck, Shield, Brain, CheckSquare, Search, Eye, Cpu, Activity } from 'lucide-react';

export default function TopologyVisualizer({
  topology = 'STAR',
  nodes = [],
  edges = [],
  highlightSender = null,
  highlightReceiver = null,
  height = 360,
  isPreview = false,
}) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);

  const topoName = (topology || 'STAR').toUpperCase();
  const nodeCount = nodes.length || 6;

  // Geometry: Calculate positions for agents in SVG coordinate space (viewBox 0 0 500 360)
  const width = 500;
  const cx = width / 2;
  const cy = height / 2;
  const radius = 125;

  const nodePositions = {};

  if (topoName === 'STAR') {
    // Center node is Agent 1
    nodes.forEach((n, idx) => {
      if (idx === 0 || n.id === 'agent_1' || n.role === 'Coordinator' || n.is_central) {
        nodePositions[n.id] = { x: cx, y: cy };
      } else {
        // Distribute remaining peripheral nodes evenly around the circle
        const pIdx = idx - 1;
        const pCount = nodeCount - 1;
        const angle = (pIdx * 2 * Math.PI) / pCount - Math.PI / 2;
        nodePositions[n.id] = {
          x: cx + radius * Math.cos(angle),
          y: cy + radius * Math.sin(angle),
        };
      }
    });
  } else {
    // Chain, Mesh, and Emergent: Regular polygon ring around center
    nodes.forEach((n, idx) => {
      const angle = (idx * 2 * Math.PI) / nodeCount - Math.PI / 2;
      nodePositions[n.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      };
    });
  }

  // Detect if this is a static preview before experiment execution
  const isStaticPreview = isPreview || edges.every((e) => !e.weight || e.weight === 0 || (e.weight === 1 && (!e.label || e.label === '1 msgs' || e.label === '0 msgs')));

  // Theoretical metrics calculation for preview mode
  const getTheoreticalMetrics = (node) => {
    const isCentral = node.is_central || node.id === 'agent_1' || node.role === 'Coordinator';
    const N = nodeCount;

    if (topoName === 'STAR') {
      if (isCentral) {
        return {
          degree: (N - 1) * 2,
          in_degree: N - 1,
          out_degree: N - 1,
          betweenness: 1.0,
          role_desc: 'Central Communication Hub (Sole message router)',
        };
      }
      return {
        degree: 2,
        in_degree: 1,
        out_degree: 1,
        betweenness: 0.0,
        role_desc: 'Peripheral Agent (Communicates exclusively with Coordinator)',
      };
    }

    if (topoName === 'CHAIN') {
      return {
        degree: 2,
        in_degree: 1,
        out_degree: 1,
        betweenness: Number((1 / Math.max(N, 1)).toFixed(3)),
        role_desc: 'Sequential Pipeline Node (Receives from prev, sends to next)',
      };
    }

    if (topoName === 'MESH') {
      return {
        degree: (N - 1) * 2,
        in_degree: N - 1,
        out_degree: N - 1,
        betweenness: 0.0,
        role_desc: 'All-to-All Peer (Direct bilateral links with all agents)',
      };
    }

    // UNCONSTRAINED / EMERGENT
    return {
      degree: 'Adaptive',
      in_degree: 'Dynamic',
      out_degree: 'Dynamic',
      betweenness: 'Emergent',
      role_desc: 'Self-Organizing Agent (Organic peer targeting & broadcast)',
    };
  };

  const getNodeColor = (role, isCentral) => {
    if (isCentral || role === 'Coordinator') return '#38bdf8';
    if (role === 'Solver') return '#818cf8';
    if (role === 'Critic') return '#f43f5e';
    if (role === 'Fact Checker') return '#fbbf24';
    if (role === 'Alternative Solver') return '#34d399';
    return '#c084fc';
  };

  return (
    <div style={{ position: 'relative', width: '100%', background: 'var(--graph-bg)', borderRadius: 12, border: '1px solid var(--graph-border)', overflow: 'hidden' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 16px', borderBottom: '1px solid var(--graph-border)', background: 'var(--graph-header)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            {isStaticPreview ? 'TOPOLOGY GRAPH PREVIEW' : 'COMMUNICATION NETWORK GRAPH'}
          </span>
          <span style={{ fontSize: 11, background: 'var(--bg-card)', padding: '2px 8px', borderRadius: 4, color: 'var(--text-muted)', border: '1px solid var(--border-color)' }}>
            {nodes.length} Nodes • {edges.length} Directed Links
          </span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Hover node to inspect agent metrics & model
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height, display: 'block' }}>
        <defs>
          {/* Arrowhead markers */}
          <marker id="arrow-default" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />
          </marker>
          <marker id="arrow-active" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
          </marker>
          <marker id="arrow-highlight" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#22c55e" />
          </marker>
          <marker id="arrow-emergent" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b" />
          </marker>
        </defs>

        {/* Render Edges */}
        {edges.map((edge, idx) => {
          const sourcePos = nodePositions[edge.source];
          const targetPos = nodePositions[edge.target];
          if (!sourcePos || !targetPos) return null;

          const isHighlight =
            (highlightSender === edge.source && highlightReceiver === edge.target) ||
            (hoveredNode === edge.source || hoveredNode === edge.target);

          const isEmergentTopo = topoName === 'UNCONSTRAINED' || topoName === 'EMERGENT';
          const strokeColor = isHighlight
            ? '#38bdf8'
            : isEmergentTopo
            ? 'rgba(245, 158, 11, 0.45)'
            : 'rgba(56, 189, 248, 0.35)';
          const strokeWidth = isHighlight ? 2.5 : 1.5;
          const markerId = isHighlight
            ? 'url(#arrow-active)'
            : isEmergentTopo
            ? 'url(#arrow-emergent)'
            : 'url(#arrow-default)';

          // Offset curve for bidirectional edges so forward and backward paths are distinctly visible
          const dx = targetPos.x - sourcePos.x;
          const dy = targetPos.y - sourcePos.y;
          const midX = (sourcePos.x + targetPos.x) / 2 - dy * 0.07;
          const midY = (sourcePos.y + targetPos.y) / 2 + dx * 0.07;

          const pathD = `M ${sourcePos.x} ${sourcePos.y} Q ${midX} ${midY} ${targetPos.x} ${targetPos.y}`;

          return (
            <g key={`edge-${idx}`} onMouseEnter={() => setHoveredEdge(edge)} onMouseLeave={() => setHoveredEdge(null)}>
              <path
                d={pathD}
                fill="none"
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                markerEnd={markerId}
                style={{ transition: 'stroke 0.2s, stroke-width 0.2s' }}
              />
              {/* Midpoint message count tag only in post-experiment mode when messages were actually sent */}
              {!isStaticPreview && edge.weight > 0 && (isHighlight || hoveredEdge === edge) && (
                <text
                  x={midX}
                  y={midY - 4}
                  fill="var(--text-secondary)"
                  fontSize="10"
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="middle"
                >
                  {edge.weight} msgs
                </text>
              )}
            </g>
          );
        })}

        {/* Render Nodes */}
        {nodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;

          const isHovered = hoveredNode === node.id;
          const isSender = highlightSender === node.id;
          const isReceiver = highlightReceiver === node.id;
          const color = getNodeColor(node.role, node.is_central);

          const r = node.role === 'Coordinator' ? 22 : 18;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Outer halo */}
              {(isHovered || isSender || isReceiver) && (
                <circle
                  r={r + 8}
                  fill="none"
                  stroke={color}
                  strokeWidth="2"
                  opacity={0.4}
                  style={{ animation: 'pulse-ring 1.5s infinite' }}
                />
              )}

              {/* Node Body */}
              <circle
                r={r}
                fill="var(--bg-card)"
                stroke={color}
                strokeWidth={isHovered ? 3 : 2}
                style={{ transition: 'all 0.15s ease' }}
              />

              {/* Node ID label */}
              <text
                textAnchor="middle"
                dy="4"
                fill="var(--text-primary)"
                fontSize={node.role === 'Coordinator' ? '11' : '10'}
                fontWeight="600"
                fontFamily="JetBrains Mono, monospace"
              >
                {node.id.replace('agent_', 'A')}
              </text>

              {/* Role Title below node */}
              <text
                textAnchor="middle"
                y={r + 14}
                fill={isHovered ? '#f8fafc' : '#94a3b8'}
                fontSize="10"
                fontWeight="500"
                fontFamily="Inter, sans-serif"
              >
                {node.role}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Centrality & Agent Inspection Tooltip Card */}
      {hoveredNode && (
        <div
          style={{
            position: 'absolute',
            bottom: 12,
            left: 12,
            background: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(10px)',
            border: '1px solid #334155',
            borderRadius: 8,
            padding: '12px 16px',
            fontSize: 12,
            color: '#f8fafc',
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            maxWidth: 340,
            zIndex: 20,
          }}
        >
          {(() => {
            const n = nodes.find((item) => item.id === hoveredNode);
            if (!n) return null;
            const theoretical = getTheoreticalMetrics(n);
            const isCoord = n.role === 'Coordinator';
            const agentLabel = n.id.replace('agent_', 'Agent ');

            return (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #334155', paddingBottom: 6 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, color: getNodeColor(n.role, n.is_central) }}>
                    {agentLabel}: {n.role}
                  </div>
                  {n.provider && (
                    <span style={{ fontSize: 9, background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', padding: '1px 5px', borderRadius: 3, textTransform: 'uppercase' }}>
                      {n.provider} {n.is_local ? '(LOCAL)' : '(CLOUD)'}
                    </span>
                  )}
                </div>

                {/* Assigned Model info */}
                {n.model && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#e2e8f0', background: 'rgba(0,0,0,0.3)', padding: '3px 8px', borderRadius: 4 }}>
                    <Cpu size={12} color="#38bdf8" />
                    <span className="mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{n.model}</span>
                  </div>
                )}

                {/* Topology role description */}
                <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                  {theoretical.role_desc}
                </div>

                {/* Metrics Table */}
                <div style={{ color: '#94a3b8', display: 'grid', gridTemplateColumns: 'auto auto', gap: '3px 12px', marginTop: 2, fontSize: 11 }}>
                  <span>Betweenness Centrality:</span>
                  <span className="mono" style={{ color: '#38bdf8', fontWeight: 600 }}>
                    {n.betweenness_centrality !== undefined && n.betweenness_centrality !== 0 ? n.betweenness_centrality : theoretical.betweenness}
                  </span>

                  <span>Topology Degree:</span>
                  <span className="mono">
                    {n.degree !== undefined && n.degree !== 0
                      ? `${n.degree} (In: ${n.in_degree}, Out: ${n.out_degree})`
                      : typeof theoretical.degree === 'number'
                      ? `${theoretical.degree} (In: ${theoretical.in_degree}, Out: ${theoretical.out_degree})`
                      : theoretical.degree}
                  </span>

                  {!isStaticPreview && (
                    <>
                      <span>Deliberation Messages:</span>
                      <span className="mono">Sent: {n.messages_sent ?? 0} | Recv: {n.messages_received ?? 0}</span>
                    </>
                  )}
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}
