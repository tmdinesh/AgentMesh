import React, { useState, useEffect } from 'react';
import { PlayCircle, Zap, RefreshCw, Trash2, ArrowUpRight, BarChart2, Layers, CheckCircle, ShieldAlert, Activity, Eye } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, Cell, PieChart, Pie } from 'recharts';
import StatCard from '../components/StatCard';
import TopologyBadge from '../components/TopologyBadge';
import FailureBadge from '../components/FailureBadge';
import LoadingState from '../components/LoadingState';
import MetricTooltip from '../components/MetricTooltip';
import { api } from '../services/api';
import { formatDateTime } from '../utils/date';

export default function DashboardPage({ onSelectExperiment, onRunNew }) {
  const [summary, setSummary] = useState(null);
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filterTopology, setFilterTopology] = useState('ALL');
  const [filterSuccess, setFilterSuccess] = useState('ALL');

  const loadData = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    else setLoading(true);
    try {
      const [sumData, expData] = await Promise.all([
        api.getResultsSummary(),
        api.getExperiments()
      ]);
      setSummary(sumData);
      setExperiments(expData);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Delete this experiment record?')) return;
    try {
      await api.deleteExperiment(id);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Are you sure you want to reset all experiment records?')) return;
    try {
      await api.clearAllExperiments();
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  // Prepare chart data
  const topologyAccuracyData = (summary?.topologies || []).map((t) => ({
    name: t.topology,
    Accuracy: t.accuracy,
    FailureRate: t.failure_rate,
    AvgMessages: t.avg_messages,
    TotalRuns: t.total_runs,
  }));

  const failureColors = {
    'No Failure': '#22c55e',
    'Wrong Final Answer': '#ef4444',
    'Hallucination / Unsupported Claim': '#f43f5e',
    'Contradiction': '#e11d48',
    'Premature Agreement': '#f59e0b',
    'Information Loss': '#fb923c',
  };

  const failurePieData = Object.entries(summary?.failure_distribution || {}).map(([name, value]) => ({
    name,
    value,
    color: failureColors[name] || '#94a3b8',
  }));

  const filteredExperiments = experiments.filter((e) => {
    if (filterTopology !== 'ALL' && e.topology !== filterTopology) return false;
    if (filterSuccess === 'SUCCESS' && !e.success) return false;
    if (filterSuccess === 'FAILED' && e.success) return false;
    return true;
  });

  if (loading && !summary) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '100px 0' }}>
        <LoadingState label="Loading Research Telemetry & Trial Records" variant="Orbit" size="lg" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Top Banner & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
            Telemetry Research Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
            Aggregated empirical results, consensus accuracy metrics, and failure taxonomy distributions across topologies.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => loadData(true)}
            className="btn btn-secondary"
            disabled={isRefreshing}
            title="Refresh dashboard data"
          >
            <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
            <span>{isRefreshing ? 'Polling...' : 'Refresh Telemetry'}</span>
          </button>
          <button onClick={onRunNew} className="btn btn-primary">
            <PlayCircle size={16} />
            <span>Launch Experiment</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
        <StatCard
          title="Total Trials"
          metric="sample_size"
          value={summary?.total_experiments ?? 0}
          subtitle={`Across ${summary?.tasks_tested_count ?? 0} benchmark tasks`}
          icon={Layers}
          color="blue"
        />
        <StatCard
          title="Cluster Accuracy"
          metric="accuracy"
          value={`${summary?.overall_accuracy ?? 0}%`}
          subtitle="Consensus accuracy across trials"
          icon={CheckCircle}
          color="green"
        />
        <StatCard
          title="Topologies Benchmarked"
          value={(summary?.topologies || []).filter((t) => t.total_runs > 0).length}
          subtitle="All 8 Topologies (Actor, Stream, Distributed, etc.)"
          icon={BarChart2}
          color="purple"
        />
        <StatCard
          title="Failure Modes Recorded"
          metric="failure_rate"
          value={Object.keys(summary?.failure_distribution || {}).filter((k) => k !== 'No Failure').length}
          subtitle="MAST failure taxonomy classifications"
          icon={ShieldAlert}
          color="amber"
        />
      </div>

      {/* Analytics Visualizations */}
      {summary?.total_experiments > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: 20 }}>
          {/* Chart 1: Accuracy & Messages by Topology */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Topology Accuracy & Message Load
              </h3>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>STAR • CHAIN • MESH • EMERGENT</span>
            </div>
            <div className="bezel-screen" style={{ width: '100%', height: 270, padding: 10 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topologyAccuracyData} margin={{ top: 15, right: 20, left: -10, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 12 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                  <Bar dataKey="Accuracy" fill="#38bdf8" radius={[4, 4, 0, 0]} name="Accuracy (%)" />
                  <Bar dataKey="AvgMessages" fill="#a855f7" radius={[4, 4, 0, 0]} name="Avg Messages / Run" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Failure Distribution */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Failure Taxonomy Breakdown
              </h3>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>ALL EXECUTED RUNS</span>
            </div>
            <div className="bezel-screen" style={{ width: '100%', height: 270, display: 'flex', alignItems: 'center', padding: 10 }}>
              {failurePieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={failurePieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={95}
                      paddingAngle={4}
                      dataKey="value"
                      label={({ name, percent }) => `${name.split('/')[0]} (${(percent * 100).toFixed(0)}%)`}
                      labelLine={false}
                      fontSize={10}
                    >
                      {failurePieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ width: '100%', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  No failure data recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Experiments History Table */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Experimental Trial Registry
            </h3>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Showing {filteredExperiments.length} of {experiments.length} total runs
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Filter by Topology */}
            <select
              value={filterTopology}
              onChange={(e) => setFilterTopology(e.target.value)}
              className="form-select"
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              <option value="ALL">All Topologies (8)</option>
              <option value="STAR">Star</option>
              <option value="CHAIN">Chain</option>
              <option value="MESH">Mesh</option>
              <option value="TREE">Tree</option>
              <option value="UNCONSTRAINED">Emergent / Unconstrained</option>
              <option value="ACTOR">Actor (Ray)</option>
              <option value="STREAM">Stream (Kafka)</option>
              <option value="DISTRIBUTED_STATE">Distributed State (etcd)</option>
            </select>

            {/* Filter by Status */}
            <select
              value={filterSuccess}
              onChange={(e) => setFilterSuccess(e.target.value)}
              className="form-select"
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              <option value="ALL">All Outcomes</option>
              <option value="SUCCESS">Success Only</option>
              <option value="FAILED">Failures Only</option>
            </select>

            {experiments.length > 0 && (
              <button onClick={handleClearAll} className="btn btn-danger" style={{ fontSize: 12, padding: '6px 12px' }}>
                <Trash2 size={13} />
                <span>Reset Database</span>
              </button>
            )}
          </div>
        </div>

        {filteredExperiments.length === 0 ? (
          <div className="bezel-screen" style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
            <div style={{ marginBottom: 12, fontSize: 14 }}>No trial records matching current filters.</div>
            <button onClick={onRunNew} className="btn btn-primary">
              <PlayCircle size={15} />
              <span>Launch a Trial</span>
            </button>
          </div>
        ) : (
          <div className="bezel-screen" style={{ overflowX: 'auto', padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Trial ID</th>
                  <th>Task Title</th>
                  <th>Topology</th>
                  <th>Agents</th>
                  <th>Turns</th>
                  <th>Status</th>
                  <th>
                    <MetricTooltip metric="primary_failure">Failure Mode</MetricTooltip>
                  </th>
                  <th>Timestamp</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredExperiments.map((exp) => (
                  <tr
                    key={exp.id}
                    onClick={() => onSelectExperiment(exp.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--accent-star)', fontWeight: 700 }}>
                        #{exp.id.substring(0, 8)}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>
                        {exp.task?.title || exp.task_title || exp.task_id}
                      </div>
                      {exp.task?.category && (
                        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{exp.task.category}</div>
                      )}
                    </td>
                    <td>
                      <TopologyBadge topology={exp.topology} />
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>
                      {exp.num_agents}
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>
                      {exp.turns_taken ?? exp.total_turns ?? exp.max_turns ?? 0}
                    </td>
                    <td>
                      <span
                        className="mono"
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: exp.success ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: exp.success ? '#4ade80' : '#f87171',
                          border: `1px solid ${exp.success ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                        }}
                      >
                        {exp.success ? 'SUCCESS' : 'FAILED'}
                      </span>
                    </td>
                    <td>
                      <FailureBadge failureType={exp.failure_type} success={exp.success} />
                    </td>
                    <td className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {formatDateTime(exp.created_at)}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectExperiment(exp.id);
                          }}
                          className="btn btn-secondary"
                          style={{ padding: '4px 8px', fontSize: 11 }}
                          title="Inspect trial details"
                        >
                          <Eye size={12} />
                          <span>Inspect</span>
                        </button>
                        <button
                          onClick={(e) => handleDelete(exp.id, e)}
                          className="btn btn-danger"
                          style={{ padding: '4px 6px', fontSize: 11 }}
                          title="Delete trial"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
