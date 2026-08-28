import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  X,
  FileText,
  HelpCircle,
  ShieldCheck,
  Check,
  MessageSquare,
  Sparkles,
  Info
} from 'lucide-react';
import TopologyBadge from './TopologyBadge';
import FailureBadge from './FailureBadge';
import { api } from '../services/api';

const FAILURE_OPTIONS = [
  { value: 'Wrong Final Answer', label: 'Wrong Final Answer', desc: 'Calculation, deduction, or arithmetic error.' },
  { value: 'Hallucination / Unsupported Claim', label: 'Hallucination / Unsupported Claim', desc: 'Fabricated non-existent constants, entities, or rules.' },
  { value: 'Contradiction', label: 'Contradiction', desc: 'Intermediate step or final answer directly contradicts a prior premise.' },
  { value: 'Premature Agreement', label: 'Premature Agreement', desc: 'Agents hastily accepted an unverified candidate without adversarial critique.' },
  { value: 'Information Loss', label: 'Information Loss', desc: 'Key constraints or findings were dropped/corrupted across communication hops.' },
  { value: 'Custom / Other', label: 'Custom / Other', desc: 'Other human-specified reasoning error.' }
];

export default function HumanVerificationModal({ experiment, isOpen, onClose, onAuditComplete }) {
  if (!isOpen || !experiment) return null;

  const [isSuccess, setIsSuccess] = useState(experiment.success ?? false);
  const [failureType, setFailureType] = useState(
    experiment.failure_type && experiment.failure_type !== 'No Failure'
      ? experiment.failure_type
      : 'Wrong Final Answer'
  );
  const [failureReason, setFailureReason] = useState(experiment.failure_reason || '');
  const [humanNotes, setHumanNotes] = useState(experiment.human_notes || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    if (experiment) {
      setIsSuccess(Boolean(experiment.success));
      setFailureType(
        experiment.failure_type && experiment.failure_type !== 'No Failure'
          ? experiment.failure_type
          : 'Wrong Final Answer'
      );
      setFailureReason(experiment.failure_reason || '');
      setHumanNotes(experiment.human_notes || '');
      setErrorMessage(null);
    }
  }, [experiment]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = {
        success: isSuccess,
        failure_type: isSuccess ? 'No Failure' : failureType,
        failure_reason: isSuccess
          ? 'Verified correct by human auditor.'
          : (failureReason.trim() || `Human verified failure: ${failureType}`),
        human_notes: humanNotes.trim() || null
      };

      const updated = await api.auditExperiment(experiment.id, payload);
      if (onAuditComplete) {
        onAuditComplete(updated);
      }
      onClose();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to apply human audit.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.82)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: 20,
        animation: 'fadeIn 0.2s ease-out'
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: 760,
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-focus)',
          boxShadow: '0 0 40px rgba(56, 189, 248, 0.15), var(--panel-shadow)',
          borderRadius: 14,
          padding: 0,
          overflow: 'hidden',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 8,
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8'
              }}
            >
              <UserCheck size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                  Human Verification & Audit
                </h3>
                <TopologyBadge topology={experiment.topology} />
                {experiment.human_audited && (
                  <span
                    className="mono"
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: 4,
                      background: 'rgba(168, 85, 247, 0.2)',
                      color: '#c084fc',
                      border: '1px solid rgba(168, 85, 247, 0.4)'
                    }}
                  >
                    PREVIOUSLY AUDITED
                  </span>
                )}
              </div>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Trial #{experiment.id.substring(0, 10)} • {experiment.num_agents} Agents • Automated Verdict:{' '}
                <strong style={{ color: experiment.success ? '#4ade80' : '#f87171' }}>
                  {experiment.success ? 'SUCCESS' : 'FAILED'}
                </strong>
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
              padding: 6,
              borderRadius: 6
            }}
            title="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
          {errorMessage && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 8,
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#fca5a5',
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8
              }}
            >
              <AlertTriangle size={15} color="#ef4444" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Section 1: Problem & Ground Truth Reference */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div
              className="bezel-screen"
              style={{
                background: 'var(--bg-inner)',
                padding: 14,
                borderRadius: 8,
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: 6
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-star)', textTransform: 'uppercase' }}>
                  Task: {experiment.task?.title || experiment.task_id}
                </span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  {experiment.task?.category || 'Benchmark'}
                </span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>
                {experiment.task?.question || 'No question details available.'}
              </div>
            </div>

            {/* Expected Answer & Criteria */}
            {(experiment.task?.expected_answer || experiment.expected_answer) && (
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  borderRadius: 8,
                  padding: 12,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, color: '#34d399', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Ground-Truth Expected Solution & Criteria:
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {experiment.task?.expected_answer || experiment.expected_answer}
                </div>
                {experiment.task?.evaluation_criteria && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    <strong>Criteria:</strong> {experiment.task.evaluation_criteria}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section 2: Agent Team Produced Output */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-primary)' }}>
                Agent Team's Produced Final Answer:
              </label>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Automated Eval: <FailureBadge failureType={experiment.failure_type} success={experiment.success} />
              </span>
            </div>
            <div
              className="bezel-screen"
              style={{
                background: 'var(--bg-inner)',
                padding: 14,
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                fontSize: 13,
                color: 'var(--text-primary)',
                lineHeight: 1.6,
                maxHeight: 160,
                overflowY: 'auto',
                whiteSpace: 'pre-wrap'
              }}
            >
              {experiment.final_answer || 'No final answer was generated by the coordinator.'}
            </div>
          </div>

          {/* Section 3: Human Verification Decision */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-primary)' }}>
              Human Auditor Determination:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {/* Option 1: Verified Correct */}
              <button
                type="button"
                onClick={() => setIsSuccess(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: isSuccess ? '2px solid #22c55e' : '1px solid var(--border-color)',
                  background: isSuccess ? 'rgba(34, 197, 94, 0.15)' : 'var(--bg-secondary)',
                  cursor: 'pointer',
                  color: isSuccess ? '#4ade80' : 'var(--text-secondary)',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: isSuccess ? '#22c55e' : 'rgba(255,255,255,0.05)',
                    color: isSuccess ? '#000' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <CheckCircle2 size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>Verify as Correct (PASS)</div>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>Solution fully satisfies reasoning invariants</div>
                </div>
              </button>

              {/* Option 2: Verified Incorrect */}
              <button
                type="button"
                onClick={() => setIsSuccess(false)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: !isSuccess ? '2px solid #ef4444' : '1px solid var(--border-color)',
                  background: !isSuccess ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-secondary)',
                  cursor: 'pointer',
                  color: !isSuccess ? '#f87171' : 'var(--text-secondary)',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: !isSuccess ? '#ef4444' : 'rgba(255,255,255,0.05)',
                    color: !isSuccess ? '#fff' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <XCircle size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>Verify as Incorrect (FAIL)</div>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>Answer contains logical or factual flaws</div>
                </div>
              </button>
            </div>
          </div>

          {/* Section 4: If Failed, Taxonomy Classification */}
          {!isSuccess && (
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.05)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 8,
                padding: 14,
                display: 'flex',
                flexDirection: 'column',
                gap: 12
              }}
            >
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Assign Primary Failure Taxonomy Mode:
                </label>
                <select
                  value={failureType}
                  onChange={(e) => setFailureType(e.target.value)}
                  className="form-select"
                  style={{ width: '100%', marginTop: 6, fontSize: 13 }}
                >
                  {FAILURE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label} — {opt.desc}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Failure Root Cause & Diagnostic Reason:
                </label>
                <input
                  type="text"
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  placeholder="e.g. Coordinator accepted premature hypothesis without verifying constraints..."
                  className="form-input"
                  style={{ width: '100%', marginTop: 4, fontSize: 12 }}
                />
              </div>
            </div>
          )}

          {/* Section 5: Auditor Commentary & Notes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-primary)' }}>
              Human Auditor Research Notes (Optional):
            </label>
            <textarea
              value={humanNotes}
              onChange={(e) => setHumanNotes(e.target.value)}
              placeholder="Add your qualitative research observations, reason for override, or notes for mentor review..."
              rows={2}
              className="form-textarea"
              style={{ width: '100%', fontSize: 12, lineHeight: 1.5 }}
            />
          </div>

          {/* Modal Actions Footer */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'center',
              gap: 12,
              borderTop: '1px solid var(--border-color)',
              paddingTop: 16,
              marginTop: 6
            }}
          >
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              style={{ fontSize: 13, padding: '8px 18px' }}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              style={{
                fontSize: 13,
                padding: '8px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: isSuccess
                  ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                  : 'linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)'
              }}
              disabled={isSubmitting}
            >
              <ShieldCheck size={16} />
              <span>{isSubmitting ? 'Applying Audit...' : 'Confirm & Apply Audit'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
