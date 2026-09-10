import React from 'react';
import { Network, PlayCircle, BarChart3, BookOpen, Layers, Sun, Moon, Cpu, Activity } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthInfo, theme = 'dark', onToggleTheme }) {
  const tabs = [
    { id: 'dashboard', label: 'Telemetry Dashboard', icon: BarChart3 },
    { id: 'run', label: 'Experiment Runner', icon: PlayCircle },
    { id: 'compare', label: 'Topology Analysis', icon: Layers },
    { id: 'tasks', label: 'Benchmark Catalog', icon: BookOpen },
  ];

  return (
    <header
      style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
      }}
    >
      <div
        style={{
          maxWidth: 1440,
          margin: '0 auto',
          padding: '0 32px',
          height: 68,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {/* Brand Instrument Title */}
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer' }}
          onClick={() => setActiveTab('dashboard')}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #0284c7 0%, #4f46e5 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.4), 0 0 16px rgba(2, 132, 199, 0.45)',
              border: '1px solid rgba(255,255,255,0.2)',
            }}
          >
            <Network size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                MAST Topology Lab
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  background: 'rgba(56, 189, 248, 0.12)',
                  color: 'var(--accent-star)',
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontWeight: 700,
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                }}
              >
                v1.0 RESEARCH
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>
              Multi-Agent LLM Communication Topology & Failure Analysis
            </div>
          </div>
        </div>

        {/* Tactile Hardware Tabs */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--bg-inner)',
            padding: '4px 6px',
            borderRadius: 8,
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--inset-shadow)',
          }}
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 14px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  background: isActive
                    ? 'linear-gradient(180deg, var(--bg-card) 0%, var(--bg-secondary) 100%)'
                    : 'transparent',
                  color: isActive ? 'var(--accent-star)' : 'var(--text-secondary)',
                  border: isActive ? '1px solid var(--border-color)' : '1px solid transparent',
                  boxShadow: isActive ? 'inset 0 1px 0 var(--bevel-light), 0 2px 6px rgba(0,0,0,0.3)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={15} color={isActive ? 'var(--accent-star)' : 'currentColor'} />
                <span>{tab.label}</span>
                {isActive && (
                  <span
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: '50%',
                      background: 'var(--accent-star)',
                      boxShadow: '0 0 6px var(--accent-star)',
                    }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Telemetry Indicator & Theme Switch */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginLeft: 16 }}>
          {/* Engine Status Pill */}
          {healthInfo ? (
            <div
              title="Strict Zero-Simulation Mode: All agent turns invoke genuine LLMs or raise explicit errors."
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 14px',
                borderRadius: 9999,
                background: 'rgba(34, 197, 94, 0.08)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                boxShadow: '0 0 12px rgba(34, 197, 94, 0.15)',
                fontSize: 12,
              }}
            >
              <div className="pulsing-dot" style={{ background: '#22c55e', boxShadow: '0 0 8px #22c55e' }} />
              <span style={{ color: '#4ade80', fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                Live Multi-LLM (Strict Mode)
              </span>
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 9999,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
              }}
            >
              <span className="led-indicator led-amber" />
              <span>Connecting Backend...</span>
            </div>
          )}

          {/* Theme Switch Button with generous spacing */}
          <button
            onClick={onToggleTheme}
            className="btn btn-secondary"
            style={{
              padding: '7px 14px',
              borderRadius: 8,
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
            }}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? <Sun size={15} color="#fbbf24" /> : <Moon size={15} color="#6366f1" />}
            <span style={{ fontWeight: 600 }}>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
