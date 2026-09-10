import React, { useState } from 'react';
import { AlertTriangle, X, RefreshCw, Copy, Check, Key, WifiOff, ShieldAlert, Cpu } from 'lucide-react';

export default function ApiErrorModal({ error, onClose, onRetry, retryLabel = 'Retry Execution' }) {
  const [copied, setCopied] = useState(false);
  if (!error) return null;

  const errStr = typeof error === 'string' ? error : (error.detail || JSON.stringify(error));

  // Determine error category
  let category = 'LLM Gateway Error';
  let categoryIcon = <AlertTriangle size={18} color="#ef4444" />;
  let resolutionSteps = [
    'Verify that your API keys are configured properly in backend/.env.',
    'Check network connectivity or switch to another supported LLM model in the agent rack.'
  ];

  if (errStr.toLowerCase().includes('missing api key') || errStr.toLowerCase().includes('no api key') || errStr.toLowerCase().includes('unauthorized') || errStr.toLowerCase().includes('401')) {
    category = 'Missing API Key';
    categoryIcon = <Key size={18} color="#f59e0b" />;
    resolutionSteps = [
      'Open the backend environment file: backend/.env',
      'Set AICREDITS_API_KEY="your_api_key_here" (or set agent-specific keys like AGENT_1_API_KEY).',
      'Restart the backend server to load the updated credentials.'
    ];
  } else if (errStr.toLowerCase().includes('cannot connect') || errStr.toLowerCase().includes('connection refused') || errStr.toLowerCase().includes('ollama not running')) {
    category = 'Local Endpoint Offline';
    categoryIcon = <WifiOff size={18} color="#f43f5e" />;
    resolutionSteps = [
      'If using local Ollama (Agent 6), start Ollama on your machine: ollama run llama3',
      'Or change Agent 6 model to a cloud model (e.g. OpenAI GPT-OSS 120B) in the Agent Registry Rack above.',
      'Ensure the Ollama port 11434 is accessible.'
    ];
  } else if (errStr.toLowerCase().includes('rate limit') || errStr.toLowerCase().includes('429')) {
    category = 'Rate Limit / Quota Exceeded';
    categoryIcon = <ShieldAlert size={18} color="#fbbf24" />;
    resolutionSteps = [
      'Wait a few seconds for the rate limit window to reset.',
      'Reduce the number of agents or max deliberation turns.',
      'Or switch affected agents to alternate models in the cluster.'
    ];
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(errStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
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
          maxWidth: 580,
          background: 'var(--bg-card)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          boxShadow: '0 0 35px rgba(239, 68, 68, 0.25), var(--panel-shadow)',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {categoryIcon}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f87171', margin: 0 }}>
                  Strict LLM Execution Error
                </h3>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 999,
                    background: 'rgba(239, 68, 68, 0.2)',
                    color: '#fca5a5',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    textTransform: 'uppercase',
                  }}
                >
                  {category}
                </span>
              </div>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Zero-Simulation Policy: Execution aborted to maintain rigorous empirical standards.
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

        {/* Error Details Box with Copy Button */}
        <div style={{ position: 'relative' }}>
          <div
            className="bezel-screen mono"
            style={{
              padding: '12px 40px 12px 14px',
              fontSize: 12,
              lineHeight: 1.5,
              color: '#fca5a5',
              background: 'var(--bg-inner)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              maxHeight: 160,
              overflowY: 'auto',
              wordBreak: 'break-word',
              borderRadius: 8,
            }}
          >
            {errStr}
          </div>
          <button
            onClick={handleCopy}
            title="Copy Error to Clipboard"
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              color: copied ? '#4ade80' : 'var(--text-secondary)',
              borderRadius: 6,
              padding: '4px 8px',
              fontSize: 11,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>

        {/* Diagnostic Guidance */}
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <strong style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>Actionable Resolution Steps:</span>
          </strong>
          <ol style={{ paddingLeft: 20, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {resolutionSteps.map((step, idx) => (
              <li key={idx} style={{ color: 'var(--text-secondary)' }}>
                {step}
              </li>
            ))}
          </ol>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: 14 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Need help? Check <code>backend/README.md</code> or documentation.
          </span>

          <div style={{ display: 'flex', gap: 10 }}>
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
    </div>
  );
}

