import React from 'react';
import MetricTooltip from './MetricTooltip';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue', trend = null, metric = null }) {
  const colorMap = {
    blue: { bg: 'rgba(56, 189, 248, 0.12)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)', led: 'led-blue' },
    purple: { bg: 'rgba(168, 85, 247, 0.12)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.35)', led: 'led-blue' },
    green: { bg: 'rgba(34, 197, 94, 0.12)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.35)', led: 'led-green' },
    amber: { bg: 'rgba(245, 158, 11, 0.12)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.35)', led: 'led-amber' },
    rose: { bg: 'rgba(244, 63, 94, 0.12)', text: '#fb7185', border: 'rgba(244, 63, 94, 0.35)', led: 'led-amber' },
  };

  const scheme = colorMap[color] || colorMap.blue;

  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className={`led-indicator ${scheme.led}`} />
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)' }}>
            {metric ? <MetricTooltip metric={metric} showIcon>{title}</MetricTooltip> : title}
          </span>
        </div>
        {Icon && (
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: scheme.bg,
              border: `1px solid ${scheme.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: scheme.text,
              boxShadow: `0 0 10px ${scheme.bg}`,
            }}
          >
            <Icon size={16} />
          </div>
        )}
      </div>

      {/* Recessed Value Display Box */}
      <div
        className="bezel-screen"
        style={{
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: '-0.02em',
            color: 'var(--text-primary)',
            textShadow: '0 0 12px rgba(255,255,255,0.15)',
          }}
        >
          {value}
        </span>
        {trend && (
          <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: trend > 0 ? '#4ade80' : '#f87171' }}>
            {trend > 0 ? `+${trend}%` : `${trend}%`}
          </span>
        )}
      </div>

      {subtitle && (
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>
          {subtitle}
        </span>
      )}
    </div>
  );
}
