import React, { useState } from 'react';
import { Network, Star, GitCommit, GitBranch, Activity, CheckCircle2, AlertTriangle, ArrowRight, ShieldAlert, Award, FileText } from 'lucide-react';
import TopologyBadge from './TopologyBadge';
import FailureBadge from './FailureBadge';

export default function MultiTopologyComparisonRadar({ results = [], onInspectExperiment }) {
  const [selectedResult, setSelectedResult] = useState(null);

  if (!results || results.length === 0) return null;

  // Topology color mapping
  const TOPO_COLORS = {
    STAR: '#38bdf8',
    CHAIN: '#a855f7',
    MESH: '#10b981',
    TREE: '#ec4899',
    UNCONSTRAINED: '#f59e0b',
    EMERGENT: '#f59e0b',
  };

  // Dimensions for Multi-Topology SVG Radar Graph
  const size = 380;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 130;

  // 5 Radar Dimensions
  const axes = [
    { label: 'Density / Diffusion', key: 'density' },
    { label: 'Message Volume', key: 'messages' },
    { label: 'Rigor / Critical Debate', key: 'rigor' },
    { label: 'Turn Efficiency', key: 'turn_efficiency' },
    { label: 'Solution Correctness', key: 'correctness' },
  ];

  // Calculate normalized points (0 to 1) for each result
  const radarData = results.map((res) => {
    const topo = (res.topology || 'STAR').toUpperCase();
    const density = res.network_metrics?.communication_density ?? (topo === 'MESH' ? 0.9 : topo === 'STAR' ? 0.4 : topo === 'TREE' ? 0.5 : 0.2);
    const messagesNorm = Math.min(1, (res.total_messages || 8) / 25);
    const correctness = res.success ? 1.0 : 0.2;
    const turnEff = Math.max(0.1, 1 - (res.turns_taken || res.max_turns || 8) / 16);
    const rigor = topo === 'MESH' || topo === 'TREE' ? 0.9 : topo === 'STAR' ? 0.6 : 0.4;

    const values = [density, messagesNorm, rigor, turnEff, correctness];

    const points = axes.map((_, i) => {
      const angle = (i * 2 * Math.PI) / axes.length - Math.PI / 2;
      const r = radius * Math.max(0.1, Math.min(1.0, values[i]));
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    });

    const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(' ');

    return {
      topology: topo,
      color: TOPO_COLORS[topo] || '#38bdf8',
      polygonPoints,
      points,
      values,
      raw: res,
    };
  });

  // Structural Topology Failure/Success Explanations
  const getTopologicalDiagnosis = (res) => {
    const topo = (res.topology || '').toUpperCase();
    const success = res.success;

    if (success) {
      switch (topo) {
        case 'STAR':
          return 'Central Coordinator synthesized peripheral specialist inputs effectively without distraction from uncoordinated lateral messages.';
        case 'CHAIN':
          return 'Sequential pipeline maintained stepwise logical progression from problem decomposition to final verification without deviation.';
        case 'MESH':
          return 'All-to-all peer debate enabled robust adversarial stress-testing and cross-examination, catching subtle edge cases.';
        case 'TREE':
          return 'Hierarchical delegation allowed branch supervisors to verify leaf facts before reporting up to the root Coordinator.';
        case 'UNCONSTRAINED':
        case 'EMERGENT':
          return 'Dynamic self-organizing links formed natural task clusters, allowing peer models to converse based on communicative need.';
        default:
          return 'Deliberation succeeded in arriving at a coherent, verified solution.';
      }
    } else {
      switch (topo) {
        case 'STAR':
          return 'Star topology bottleneck: The Coordinator became an information choke-point, leading to premature agreement without adequate peer cross-examination.';
        case 'CHAIN':
          return 'Chain topology decay: Sequential linear pipeline suffered from information loss and premise distortion across turns.';
        case 'MESH':
          return 'Mesh topology echo: Dense unconstrained peer links caused hallucination propagation and debate circularity.';
        case 'TREE':
          return 'Tree topology isolation: Leaf specialist critiques were filtered out by branch nodes before reaching the root decider.';
        case 'UNCONSTRAINED':
        case 'EMERGENT':
          return 'Emergent communication instability: Unstructured routing led to redundant arguments and failure to converge on the true answer.';
        default:
          return res.failure_reason || 'Trial failed to satisfy verification criteria.';
      }
    }
  };

  return (
    <div
      className="card"
      style={{
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        border: '2px solid rgba(56, 189, 248, 0.3)',
        background: 'var(--bg-card)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), var(--panel-shadow)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, borderBottom: '1px solid var(--border-color)', paddingBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Award size={18} color="var(--accent-star)" />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
              Comparative Multi-Topology Post-Mortem Analytics
            </h3>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Empirical differentiation statistics, radar graph overlay, and root-cause analysis across {results.length} topologies.
            </span>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {radarData.map((d) => (
            <div
              key={d.topology}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '3px 8px',
                background: 'var(--bg-inner)',
                borderRadius: 4,
                border: `1px solid ${d.color}55`,
                fontSize: 11,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: d.color }} />
              <span className="mono" style={{ fontWeight: 700, color: d.color }}>{d.topology === 'UNCONSTRAINED' ? 'EMERGENT' : d.topology}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Comparative Grid: Radar Left, Diagnostic Cards Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20, alignItems: 'center' }}>
        {/* Left: SVG Multi-Topology Radar Overlay Chart */}
        <div
          className="bezel-screen"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            background: 'var(--bg-inner)',
            border: '1px solid var(--border-color)',
            minHeight: 380,
          }}
        >
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {/* Background Concentric Webs */}
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((level, lvlIdx) => {
              const webPoints = axes
                .map((_, i) => {
                  const angle = (i * 2 * Math.PI) / axes.length - Math.PI / 2;
                  const r = radius * level;
                  return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
                })
                .join(' ');

              return (
                <polygon
                  key={lvlIdx}
                  points={webPoints}
                  fill="none"
                  stroke="var(--border-color)"
                  strokeWidth={level === 1.0 ? '1.5' : '1'}
                  strokeDasharray={level === 1.0 ? 'none' : '3 3'}
                  opacity={0.6}
                />
              );
            })}

            {/* Radial Axis Lines */}
            {axes.map((axis, i) => {
              const angle = (i * 2 * Math.PI) / axes.length - Math.PI / 2;
              const x2 = cx + radius * Math.cos(angle);
              const y2 = cy + radius * Math.sin(angle);
              const labelX = cx + (radius + 24) * Math.cos(angle);
              const labelY = cy + (radius + 18) * Math.sin(angle);

              return (
                <g key={i}>
                  <line x1={cx} y1={cy} x2={x2} y2={y2} stroke="var(--border-color)" strokeWidth="1" opacity={0.7} />
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="var(--text-secondary)"
                    fontSize="10"
                    fontWeight="600"
                    fontFamily="var(--font-sans)"
                  >
                    {axis.label}
                  </text>
                </g>
              );
            })}

            {/* Polygons for each Topology */}
            {radarData.map((d) => (
              <g key={d.topology}>
                <polygon
                  points={d.polygonPoints}
                  fill={`${d.color}25`}
                  stroke={d.color}
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  style={{ transition: 'all 0.3s ease' }}
                />
                {d.points.map((p, pIdx) => (
                  <circle
                    key={pIdx}
                    cx={p.x}
                    cy={p.y}
                    r="4"
                    fill={d.color}
                    stroke="var(--bg-primary)"
                    strokeWidth="1.5"
                  />
                ))}
              </g>
            ))}
          </svg>
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
            Multi-Topology Performance Radar (Normalized Dimensions)
          </span>
        </div>

        {/* Right: Comparative Breakdown Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 420, overflowY: 'auto' }}>
          {results.map((res, idx) => {
            const topo = (res.topology || 'STAR').toUpperCase();
            const color = TOPO_COLORS[topo] || '#38bdf8';
            const diagnosis = getTopologicalDiagnosis(res);

            return (
              <div
                key={res.id || idx}
                className="bezel-screen"
                style={{
                  padding: 12,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                  borderLeft: `4px solid ${color}`,
                  background: 'var(--bg-inner)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <TopologyBadge topology={topo} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: res.success ? '#22c55e' : '#ef4444' }}>
                      {res.success ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FailureBadge failureType={res.failure_type || (res.success ? 'No Failure' : 'Wrong Final Answer')} />
                    {onInspectExperiment && res.id && (
                      <button
                        onClick={() => onInspectExperiment(res.id)}
                        className="btn btn-secondary"
                        style={{ padding: '2px 8px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}
                      >
                        <span>Details</span>
                        <ArrowRight size={10} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Critical Analysis: Why it Succeeded or Failed */}
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: res.success ? 'var(--text-primary)' : '#f87171' }}>
                    {res.success ? 'Topological Success Factor: ' : 'Root-Cause Failure Mechanism: '}
                  </strong>
                  {diagnosis}
                </div>

                {/* Telemetry Metrics Bar */}
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: 6 }}>
                  <span>Messages: <strong style={{ color: 'var(--text-primary)' }}>{res.total_messages || res.messages?.length || 0}</strong></span>
                  <span>Turns: <strong style={{ color: 'var(--text-primary)' }}>{res.turns_taken || res.max_turns || 0}</strong></span>
                  <span>Density: <strong style={{ color: 'var(--text-primary)' }}>{res.network_metrics?.communication_density ?? 0}</strong></span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
