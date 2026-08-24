import React, { useEffect, useState } from 'react';

/* ─────────────────────────────────────────────────────────
 * LOADING STATE — pixel-grid loader for long-running work
 *
 * Variants:
 *   Drive  — square cells, chevron wavefront driving right;
 *            the 650ms cycle is shorter than the sweep, so
 *            two fronts are always in flight
 *   Dots   — same wavefront, circular cells
 *   Orbit  — a comet lapping the grid perimeter
 *
 * Paired with a shimmering label and a live elapsed timer
 * in mono tabular figures.
 * ───────────────────────────────────────────────────────── */

const chevron = Array.from({ length: 9 }, (_, i) => {
  const r = Math.floor(i / 3),
    c = i % 3;
  return (c + Math.abs(r - 1)) * 90;
});

const ORBIT_ORDER = [0, 1, 2, 5, 8, 7, 6, 3];
const orbit = Array.from({ length: 9 }, (_, i) => {
  const k = ORBIT_ORDER.indexOf(i);
  return k === -1 ? null : k * 110;
});

const PATTERNS = {
  Drive: { delays: chevron, dur: 650, round: false },
  Dots: { delays: chevron, dur: 650, round: true },
  Orbit: { delays: orbit, dur: 950, round: false },
};

function useElapsed() {
  const [ds, setDs] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setDs((d) => d + 1), 100);
    return () => clearInterval(t);
  }, []);
  const total = ds / 10;
  if (total < 60) return `${total.toFixed(1)}s`;
  return `${Math.floor(total / 60)}m ${(total % 60).toFixed(1)}s`;
}

export default function LoadingState({
  label = "Deliberating",
  variant = "Drive",
  style = {},
  className = "",
  size = "md" // 'sm', 'md', 'lg'
}) {
  const elapsed = useElapsed();
  const { delays, dur, round } = PATTERNS[variant] ?? PATTERNS.Drive;

  const pixelSize = size === 'sm' ? 3 : size === 'lg' ? 6 : 4;
  const gapSize = size === 'sm' ? 1 : size === 'lg' ? 2 : 1.5;
  const fontSize = size === 'sm' ? 11 : size === 'lg' ? 15 : 13;
  const timerFontSize = size === 'sm' ? 10 : size === 'lg' ? 13 : 11;

  return (
    <div
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        width: 'fit-content',
        ...style
      }}
    >
      {/* 3x3 Pixel Grid */}
      <span
        aria-hidden="true"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(3, ${pixelSize}px)`,
          gap: `${gapSize}px`,
          lineHeight: 0,
        }}
      >
        {delays.map((d, i) => (
          <span
            key={i}
            style={{
              width: `${pixelSize}px`,
              height: `${pixelSize}px`,
              backgroundColor: 'var(--text-primary)',
              borderRadius: round ? '50%' : '1.5px',
              opacity: d === null ? 0.08 : 0.2,
              animation:
                d === null
                  ? 'none'
                  : `pixel-on ${dur}ms ease-in-out ${d}ms infinite`,
              display: 'inline-block',
            }}
          />
        ))}
      </span>

      {/* Shimmering Text Label */}
      <span
        style={{
          fontSize: `${fontSize}px`,
          fontWeight: 600,
          backgroundImage:
            'linear-gradient(90deg, var(--text-muted) 25%, var(--accent-star) 50%, var(--text-muted) 75%)',
          backgroundSize: '200% 100%',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          animation: 'shimmer-text 1.6s linear infinite',
          letterSpacing: '0.02em',
        }}
      >
        {label}
      </span>

      {/* Elapsed Timer */}
      <span
        className="mono"
        style={{
          fontSize: `${timerFontSize}px`,
          color: 'var(--text-muted)',
          fontVariantNumeric: 'tabular-nums',
          padding: '1px 6px',
          background: 'var(--bg-inner)',
          borderRadius: 4,
          border: '1px solid var(--border-color)',
        }}
      >
        {elapsed}
      </span>
    </div>
  );
}
