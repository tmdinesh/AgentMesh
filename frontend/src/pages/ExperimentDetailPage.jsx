import React, { useState, useEffect } from 'react';
import { ArrowLeft, CheckCircle2, AlertTriangle, Layers, MessageSquare, Network, Clock, ShieldAlert, Cpu, Activity } from 'lucide-react';
import { api } from '../services/api';
import TopologyBadge from '../components/TopologyBadge';
import FailureBadge from '../components/FailureBadge';
import TopologyVisualizer from '../components/TopologyVisualizer';
import MessageFeed from '../components/MessageFeed';
import { formatDateTime } from '../utils/date';

export default function ExperimentDetailPage({ experimentId, onBack }) {
  const [experiment, setExperiment] = useState(null);
  const [messages, setMessages] = useState([]);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    const fetchDetails = async () => {
      setLoading(true);
      try {
        const [expData, msgData, netData] = await Promise.all([
          api.getExperiment(experimentId),
          api.getExperimentMessages(experimentId),
          api.getExperimentNetwork(experimentId)
        ]);
        setExperiment(expData);
        setMessages(msgData);
        setNetwork(netData);
      } catch (err) {
        setErrorMsg(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (experimentId) fetchDetails();
  }, [experimentId]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
        Loading trial post-mortem telemetry...
      </div>
    );
  }

  if (errorMsg || !experiment) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 40 }}>
        <AlertTriangle size={32} color="#f43f5e" style={{ margin: '0 auto 16px' }} />
        <h3>Failed to load experiment {experimentId}</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{errorMsg}</p>
        <button onClick={onBack} className="btn btn-secondary">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Top Navigation & Status Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button onClick={onBack} className="btn btn-secondary" style={{ padding: '7px 14px' }}>
            <ArrowLeft size={15} /> <span>Back</span>
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 18, fontWeight: 800 }} className="mono">Trial #{experiment.id.substring(0, 12)}</h1>
              <TopologyBadge topology={experiment.topology} />
              <FailureBadge failureType={experiment.failure_type} success={experiment.success} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>
              Executed: {formatDateTime(experiment.created_at)} • {experiment.num_agents} Agents • {experiment.turns_taken} Turns • {experiment.total_messages} Messages
            </div>
          </div>
        </div>
      </div>

      {/* Task Summary Banner */}
      <div className="card" style={{ borderLeft: '4px solid var(--accent-star)', padding: 18 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-star)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
          Benchmark Task: {experiment.task?.category}
        </div>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{experiment.task?.title || experiment.task_id}</h2>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
          {experiment.task?.question}
        </div>
      </div>

      {/* Answer & Failure Mode Diagnosis */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20 }}>
        {/* Final Synthesized Answer */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle2 size={16} color={experiment.success ? '#22c55e' : '#f43f5e'} />
              Synthesized Final Answer
            </h3>
            <span
              className="mono"
              style={{
                fontSize: 10,
                fontWeight: 700,
                background: experiment.success ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: experiment.success ? '#4ade80' : '#f87171',
                border: `1px solid ${experiment.success ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              {experiment.success ? 'PASSED' : 'FAILED'}
            </span>
          </div>

          <div
            className="bezel-screen"
            style={{
              padding: 14,
              fontSize: 13,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              color: 'var(--text-primary)',
            }}
          >
            {experiment.final_answer || 'No final answer recorded.'}
          </div>

          {/* Expected Answer */}
          <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border-color)', paddingTop: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Expected Reference:</span>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, whiteSpace: 'pre-wrap' }}>
              {experiment.expected_answer}
            </div>
          </div>
        </div>

        {/* Stage 2 Failure Taxonomy Diagnosis */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShieldAlert size={16} color={experiment.success ? '#22c55e' : '#fbbf24'} />
              Evaluation & Failure Taxonomy
            </h3>
          </div>

          <div className="bezel-screen" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>PRIMARY CLASSIFICATION</span>
              <div style={{ marginTop: 4 }}>
                <FailureBadge failureType={experiment.failure_type} success={experiment.success} />
              </div>
            </div>

            <div>
              <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>ROOT CAUSE DIAGNOSIS</span>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>
                {experiment.failure_reason || (experiment.success ? 'All constraints and logical deduction steps were successfully verified.' : 'No diagnostic explanation available.')}
              </div>
            </div>
          </div>

          {/* Network Summary Stats */}
          <div style={{ marginTop: 'auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="bezel-screen" style={{ padding: 10 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Communication Density</div>
              <div className="mono" style={{ fontSize: 16, fontWeight: 800, color: 'var(--accent-star)', marginTop: 2 }}>
                {network?.communication_density ?? 0}
              </div>
            </div>
            <div className="bezel-screen" style={{ padding: 10 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Messages</div>
              <div className="mono" style={{ fontSize: 16, fontWeight: 800, color: 'var(--accent-chain)', marginTop: 2 }}>
                {experiment.total_messages} msgs
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Communication Network Graph & Node Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20 }}>
        <div className="card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 12 }}>
            Communication Topology Network
          </h3>
          <TopologyVisualizer
            topology={experiment.topology}
            nodes={network?.nodes || []}
            edges={network?.edges || []}
            height={320}
            isPreview={false}
          />
        </div>

        {/* Centrality Metrics Breakdown Table */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            NetworkX Centrality & Node Diagnostics
          </h3>
          <div className="bezel-screen" style={{ overflowX: 'auto', padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agent / Model</th>
                  <th>Degree</th>
                  <th>Betweenness</th>
                  <th>Sent</th>
                  <th>Received</th>
                </tr>
              </thead>
              <tbody>
                {(network?.nodes || []).map((n) => (
                  <tr key={n.id}>
                    <td>
                      <div style={{ fontWeight: 700, fontSize: 13 }}>{n.role}</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--accent-star)' }}>
                        {n.model_name || n.id}
                      </div>
                    </td>
                    <td className="mono" style={{ fontSize: 13 }}>{n.degree}</td>
                    <td className="mono" style={{ fontSize: 13, color: '#38bdf8', fontWeight: 700 }}>{n.betweenness_centrality}</td>
                    <td className="mono" style={{ fontSize: 13 }}>{n.messages_sent}</td>
                    <td className="mono" style={{ fontSize: 13 }}>{n.messages_received}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Chronological Communication Transcript */}
      <div className="card">
        <MessageFeed messages={messages} />
      </div>
    </div>
  );
}
