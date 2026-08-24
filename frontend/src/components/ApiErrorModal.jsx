import React from 'react';
import { AlertTriangle, X, RefreshCw, Cpu, ExternalLink } from 'lucide-react';

export default function ApiErrorModal({ error, onClose, onRetry, retryLabel = 'Retry Execution' }) {
  if (!error) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: 20,
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: 540,
          background: 'var(--bg-card)',
          border: '2px solid rgba(239, 68, 68, 0.5)',
          boxShadow: '0 0 30px rgba(239, 68, 68, 0.25), var(--panel-shadow)',
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={20} color="#ef4444" />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f87171', margin: 0 }}>
                LLM Execution / API Error
              </h3>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Provider Gateway Interruption
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Error Details Box */}
        <div
          className="bezel-screen mono"
          style={{
            padding: 12,
            fontSize: 12,
            lineHeight: 1.5,
            color: '#fca5a5',
            background: 'var(--bg-inner)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            maxHeight: 160,
            overflowY: 'auto',
            wordBreak: 'break-word',
          }}
        >
          {error}
        </div>

        {/* Diagnostic Guidance */}
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Recommended Troubleshooting:</strong>
          <ul style={{ paddingLeft: 18, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <li>
              <strong>Swap Model</strong>: If a specific remote model is down (e.g. 500 error on DeepSeek or Qwen), select a different cloud model (e.g., <em>Google Gemini 2.0 Flash</em> or <em>OpenAI GPT-OSS 120B</em>) in the Agent Cluster Rack.
            </li>
            <li>
              <strong>Check Local Ollama</strong>: If using Agent 6 (Ollama), ensure <code>ollama run llama3</code> is active on your machine.
            </li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
          <button onClick={onClose} className="btn btn-secondary" style={{ fontSize: 12, padding: '7px 16px' }}>
            Dismiss
          </button>
          {onRetry && (
            <button
              onClick={() => {
                onClose();
                onRetry();
              }}
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <RefreshCw size={13} />
              <span>{retryLabel}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
