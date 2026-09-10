import React, { useState, useEffect } from 'react';
import { Layers, RefreshCw, Star, GitCommit, Network, AlertCircle, CheckCircle2, TrendingUp, HelpCircle, BarChart3, Activity, Download, Check } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import TopologyBadge from '../components/TopologyBadge';
import LoadingState from '../components/LoadingState';
import MetricTooltip from '../components/MetricTooltip';

export default function ComparisonPage({ onRunBatch }) {
  const [statsData, setStatsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleExportDataset = async () => {
    setIsExporting(true);
    try {
      const data = await api.exportResearchDataset();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `agentmesh_research_dataset_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } catch (err) {
      alert('Failed to export research dataset: ' + err.message);
    } finally {
      setIsExporting(false);
    }
  };

  const loadStats = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    else setLoading(true);
    try {
      const data = await api.getStatisticalAnalysis();
      setStatsData(data);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const summary = statsData?.summary;
  const chi = statsData?.chi_square_analysis;
  const topologies = summary?.topologies || [];

  // Chart data formatting
  const comparisonChartData = topologies.map((t) => ({
    name: t.topology,
    Accuracy: t.accuracy,
    FailureRate: t.failure_rate,
    AvgMessages: t.avg_messages,
    Density: t.avg_density * 100,
    TotalRuns: t.total_runs,
  }));

  // Failure Breakdown across topologies for Grouped Bar Chart
  const failureKeys = [
    'No Failure',
    'Wrong Final Answer',
    'Hallucination / Unsupported Claim',
    'Contradiction',
    'Premature Agreement',
    'Information Loss',
  ];

  const failureGroupedData = topologies.map((t) => {
    const row = { name: t.topology };
    failureKeys.forEach((key) => {
      row[key] = t.failure_breakdown?.[key] || 0;
    });
    return row;
  });

  const failureColorMap = {
    'No Failure': '#22c55e',
    'Wrong Final Answer': '#ef4444',
    'Hallucination / Unsupported Claim': '#f43f5e',
    'Contradiction': '#e11d48',
    'Premature Agreement': '#f59e0b',
    'Information Loss': '#fb923c',
  };

  if (loading && !statsData) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '100px 0' }}>
        <LoadingState label="Computing Chi-Square & Empirical Topology Metrics" variant="Orbit" size="lg" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
            Topology Comparison & Statistical Hypothesis Lab
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Empirical comparative analysis and SciPy Chi-Square test of independence between Star, Chain, Mesh, and Emergent topologies.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={handleExportDataset}
            className="btn btn-primary"
            disabled={isExporting}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            title="Export complete experimental dataset as JSON for statistical modeling, academic research, and publication"
          >
            {exportSuccess ? (
              <>
                <Check size={14} color="#22c55e" />
                <span>Exported Successfully</span>
              </>
            ) : (
              <>
                <Download size={14} className={isExporting ? 'spin' : ''} />
                <span>{isExporting ? 'Generating JSON...' : 'Export Research Dataset (JSON)'}</span>
              </>
            )}
          </button>

          <button
            onClick={() => loadStats(true)}
            className="btn btn-secondary"
            disabled={isRefreshing}
            title="Refresh statistical analysis"
          >
            <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
            <span>{isRefreshing ? 'Recalculating...' : 'Recalculate Statistics'}</span>
          </button>
        </div>
      </div>

      {/* Side-by-Side Comparative Matrix Table */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Academic Research Measures & Empirical Centrality Matrix
          </h3>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Wilson Score 95% Confidence Interval & NetworkX Graph Centrality Measures
          </span>
        </div>

        <div className="bezel-screen" style={{ overflowX: 'auto', padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Topology</th>
                <th>
                  <MetricTooltip metric="sample_size">Trials (N)</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="accuracy">Accuracy [95% CI]</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="failure_rate">Failure Rate</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="density">Comm. Density</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="betweenness">Mean Betweenness (CB)</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="closeness">Mean Closeness (CC)</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="gini">Message Gini (G)</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="entropy">Shannon Entropy (H)</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="messages">Avg Msgs</MetricTooltip>
                </th>
                <th>
                  <MetricTooltip metric="primary_failure">Primary Failure Mode</MetricTooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              {topologies.map((t) => {
                const sortedFailures = Object.entries(t.failure_breakdown || {})
                  .filter(([k]) => k !== 'No Failure')
                  .sort((a, b) => b[1] - a[1]);
                const topFailure = sortedFailures.length > 0 ? `${sortedFailures[0][0]} (${sortedFailures[0][1]})` : 'None';

                return (
                  <tr key={t.topology}>
                    <td>
                      <TopologyBadge topology={t.topology} />
                    </td>
                    <td className="mono" style={{ fontSize: 13, fontWeight: 700 }}>
                      {t.total_runs}
                    </td>
                    <td>
                      <div className="mono" style={{ fontSize: 13, fontWeight: 800, color: t.accuracy >= 70 ? '#4ade80' : '#f87171' }}>
                        {t.accuracy}%
                      </div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                        [{t.ci_95_lower ?? t.accuracy}% - {t.ci_95_upper ?? t.accuracy}%]
                      </div>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13, color: t.failure_rate > 30 ? '#f87171' : '#94a3b8' }}>
                        {t.failure_rate}%
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: 13, color: '#38bdf8' }}>
                      {t.avg_density}
                    </td>
                    <td className="mono" style={{ fontSize: 13, color: '#818cf8' }}>
                      {t.avg_betweenness ?? '0.000'}
                    </td>
                    <td className="mono" style={{ fontSize: 13, color: '#2dd4bf' }}>
                      {t.avg_closeness ?? '0.000'}
                    </td>
                    <td className="mono" style={{ fontSize: 13, color: '#fbbf24' }}>
                      {t.avg_gini ?? '0.000'}
                    </td>
                    <td className="mono" style={{ fontSize: 13, color: '#f43f5e' }}>
                      {t.avg_entropy ?? '0.000'}
                    </td>
                    <td className="mono" style={{ fontSize: 13 }}>
                      {t.avg_messages}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {topFailure}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chi-Square Hypothesis Test Panel */}
      <div
        className="card"
        style={{
          borderLeft: `4px solid ${chi?.is_significant ? '#38bdf8' : '#a855f7'}`,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BarChart3 size={20} color="#38bdf8" />
            <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              <MetricTooltip metric="chi_square">
                Chi-Square Test of Independence & Effect Size (Topology vs Failure Mode)
              </MetricTooltip>
            </h3>
          </div>
          {chi?.is_sufficient_data && (
            <span className={`badge ${chi.is_significant ? 'badge-success' : 'badge-secondary'}`}>
              {chi.is_significant ? 'Statistically Significant (p < 0.05)' : 'Not Statistically Significant (p >= 0.05)'}
            </span>
          )}
        </div>

        {/* Test Statistics Output */}
        {chi?.is_sufficient_data ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
            <div className="bezel-screen" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                <MetricTooltip metric="chi_square" showIcon>Chi-Square (X²)</MetricTooltip>
              </div>
              <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent-star)', marginTop: 4 }}>
                {chi.chi_square}
              </div>
            </div>
            <div className="bezel-screen" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                <MetricTooltip metric="p_value" showIcon>p-value</MetricTooltip>
              </div>
              <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: chi.p_value < 0.05 ? '#4ade80' : '#f87171', marginTop: 4 }}>
                {chi.p_value}
              </div>
            </div>
            <div className="bezel-screen" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                <MetricTooltip metric="cramers_v" showIcon>Cramér's V (Effect Size)</MetricTooltip>
              </div>
              <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: '#22c55e', marginTop: 4 }}>
                {chi.cramers_v ?? '0.000'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
                {chi.effect_size_label || 'Effect Size'}
              </div>
            </div>
            <div className="bezel-screen" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                <MetricTooltip metric="df" showIcon>Degrees of Freedom (df)</MetricTooltip>
              </div>
              <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent-chain)', marginTop: 4 }}>
                {chi.degrees_of_freedom}
              </div>
            </div>
            <div className="bezel-screen" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                <MetricTooltip metric="sample_size" showIcon>Sample Size (N)</MetricTooltip>
              </div>
              <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>
                {chi.sample_size} trials
              </div>
            </div>
          </div>
        ) : null}

        {/* Academic Interpretation */}
        <div
          className="bezel-screen"
          style={{
            padding: 16,
            fontSize: 13,
            lineHeight: 1.6,
            color: 'var(--text-primary)',
          }}
        >
          <strong style={{ color: 'var(--accent-star)' }}>Academic Interpretation: </strong>
          {chi?.interpretation}
        </div>

        {/* Contingency Matrix Table if available */}
        {chi?.contingency_table && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: 8 }}>
              Observed Contingency Frequency Matrix (O_ij)
            </div>
            <div className="bezel-screen" style={{ overflowX: 'auto', padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Topology</th>
                    {Object.keys(Object.values(chi.contingency_table)[0] || {}).map((fName) => (
                      <th key={fName}>{fName}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(chi.contingency_table).map(([topo, fCounts]) => (
                    <tr key={topo}>
                      <td style={{ fontWeight: 700 }}>{topo}</td>
                      {Object.values(fCounts).map((cnt, idx) => (
                        <td key={idx} className="mono" style={{ fontSize: 13 }}>
                          {cnt}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Comparative Visualizations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: 20 }}>
        {/* Chart 1: Accuracy vs Avg Messages */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Topology Accuracy & Communication Overhead
          </h3>
          <div className="bezel-screen" style={{ width: '100%', height: 280, padding: 10 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonChartData} margin={{ top: 15, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
                <YAxis stroke="var(--text-muted)" fontSize={11} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Accuracy" fill="#38bdf8" name="Accuracy (%)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="AvgMessages" fill="#a855f7" name="Avg Messages" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Failure Breakdown by Topology */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Failure Mode Frequency by Topology
          </h3>
          <div className="bezel-screen" style={{ width: '100%', height: 280, padding: 10 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={failureGroupedData} margin={{ top: 15, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
                <YAxis stroke="var(--text-muted)" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {failureKeys.map((k) => (
                  <Bar key={k} dataKey={k} fill={failureColorMap[k] || '#94a3b8'} stackId="a" />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
