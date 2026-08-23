import React, { useState, useEffect } from 'react';
import { PlayCircle, Sparkles, GitCommit, Network, Activity, Users, AlertTriangle, ChevronRight, Layers, ArrowRight, Loader2, Cpu, RefreshCw, CheckCircle, Terminal, Radio } from 'lucide-react';
import { api } from '../services/api';
import TopologyBadge from '../components/TopologyBadge';
import TopologyVisualizer from '../components/TopologyVisualizer';

export default function RunExperimentPage({ onExperimentCompleted, preselectedTaskId = null }) {
  const [tasks, setTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(true);

  // Model & Agents Config State
  const [modelsConfig, setModelsConfig] = useState(null);
  const [modelsStatus, setModelsStatus] = useState(null);
  const [loadingModels, setLoadingModels] = useState(false);

  // Form State
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [selectedTopology, setSelectedTopology] = useState('STAR');
  const [numAgents, setNumAgents] = useState(6);
  const [maxTurns, setMaxTurns] = useState(8);

  // Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });
  const [executionLogs, setExecutionLogs] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  const fetchModelsData = async () => {
    setLoadingModels(true);
    try {
      const [cfg, stat] = await Promise.all([
        api.getModelsConfig(),
        api.getModelsStatus()
      ]);
      setModelsConfig(cfg);
      setModelsStatus(stat);
    } catch (err) {
      console.warn('Failed to load models status:', err);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    const fetchTasks = async () => {
      setLoadingTasks(true);
      try {
        const data = await api.getTasks();
        setTasks(data);
        if (preselectedTaskId) {
          setSelectedTaskId(preselectedTaskId);
        } else if (data.length > 0) {
          setSelectedTaskId(data[0].id);
        }
      } catch (err) {
        setErrorMsg('Failed to load benchmark tasks: ' + err.message);
      } finally {
        setLoadingTasks(false);
      }
    };

    fetchTasks();
    fetchModelsData();
  }, [preselectedTaskId]);

  const filteredTasks = tasks.filter(
    (t) => selectedCategory === 'ALL' || t.category === selectedCategory
  );

  const currentTask = tasks.find((t) => t.id === selectedTaskId);

  const handleRunSingle = async () => {
    if (!selectedTaskId) return;
    setIsRunning(true);
    setErrorMsg(null);
    setExecutionLogs([
      { text: `[INIT] Loading ${numAgents}-agent heterogeneous cluster (5 Cloud API + 1 Local Ollama)...`, time: new Date() },
      { text: `[TOPOLOGY] Routing graph initialized under ${selectedTopology} structural constraints...`, time: new Date() },
      { text: `[TASK DISPATCH] Broadcasting benchmark task to active agents...`, time: new Date() },
    ]);

    try {
      const result = await api.runExperiment({
        task_id: selectedTaskId,
        topology: selectedTopology,
        num_agents: Number(numAgents),
        max_turns: Number(maxTurns),
      });

      setExecutionLogs((prev) => [
        ...prev,
        { text: `[SYNTHESIS] Deliberation complete. Performing two-stage automated evaluation...`, time: new Date() },
        { text: `[COMPLETED] Trial finished with result ID: ${result.id} (Success: ${result.success})`, time: new Date() },
      ]);

      setTimeout(() => {
        setIsRunning(false);
        onExperimentCompleted(result.id);
      }, 700);
    } catch (err) {
      setErrorMsg(err.message);
      setIsRunning(false);
    }
  };

  const handleRunBatchSweep = async (repetitions = 3) => {
    if (!selectedTaskId) return;
    setIsBatchRunning(true);
    setErrorMsg(null);
    const topologies = ['STAR', 'CHAIN', 'MESH', 'UNCONSTRAINED'];
    const total = topologies.length * repetitions;
    setBatchProgress({ current: 0, total });

    try {
      await api.runBatchExperiments({
        task_id: selectedTaskId,
        topologies,
        num_agents: Number(numAgents),
        max_turns: Number(maxTurns),
        repetitions,
      });

      setBatchProgress({ current: total, total });
      setTimeout(() => {
        setIsBatchRunning(false);
        alert(`Completed 4-Topology Batch Sweep of ${total} trials (Star, Chain, Mesh, Emergent)!`);
        onExperimentCompleted(null);
      }, 500);
    } catch (err) {
      setErrorMsg('Batch sweep failed: ' + err.message);
      setIsBatchRunning(false);
    }
  };

  // Agent team list with assigned model names
  const previewNodes = [
    { id: 'agent_1', name: 'Coordinator', role: 'Coordinator', is_central: true, model: modelsConfig?.agents?.[0]?.model || 'deepseek/deepseek-v3.2', provider: modelsConfig?.agents?.[0]?.provider || 'aicredits', is_local: modelsConfig?.agents?.[0]?.is_local || false },
    { id: 'agent_2', name: 'Solver', role: 'Solver', is_central: false, model: modelsConfig?.agents?.[1]?.model || 'openai/gpt-oss-120b', provider: modelsConfig?.agents?.[1]?.provider || 'aicredits', is_local: modelsConfig?.agents?.[1]?.is_local || false },
    { id: 'agent_3', name: 'Critic', role: 'Critic', is_central: false, model: modelsConfig?.agents?.[2]?.model || 'qwen/qwen3-30b-a3b-instruct-2507', provider: modelsConfig?.agents?.[2]?.provider || 'aicredits', is_local: modelsConfig?.agents?.[2]?.is_local || false },
    { id: 'agent_4', name: 'Fact Checker', role: 'Fact Checker', is_central: false, model: modelsConfig?.agents?.[3]?.model || 'google/gemini-2.0-flash-lite-001', provider: modelsConfig?.agents?.[3]?.provider || 'aicredits', is_local: modelsConfig?.agents?.[3]?.is_local || false },
    { id: 'agent_5', name: 'Alternative Solver', role: 'Alternative Solver', is_central: false, model: modelsConfig?.agents?.[4]?.model || 'nex-agi/nex-n2-mini', provider: modelsConfig?.agents?.[4]?.provider || 'aicredits', is_local: modelsConfig?.agents?.[4]?.is_local || false },
    { id: 'agent_6', name: 'Final Reviewer', role: 'Final Reviewer', is_central: false, model: modelsConfig?.agents?.[5]?.model || 'llama3:8b (local)', provider: modelsConfig?.agents?.[5]?.provider || 'ollama', is_local: true },
  ].slice(0, numAgents);

  const getDynamicPreviewEdges = (topo) => {
    const ids = previewNodes.map((n) => n.id);
    const edges = [];

    if (topo === 'STAR') {
      const central = ids[0];
      for (let i = 1; i < ids.length; i++) {
        edges.push({ source: central, target: ids[i], weight: 1 });
        edges.push({ source: ids[i], target: central, weight: 1 });
      }
    } else if (topo === 'CHAIN') {
      for (let i = 0; i < ids.length; i++) {
        const next = ids[(i + 1) % ids.length];
        edges.push({ source: ids[i], target: next, weight: 1 });
      }
    } else if (topo === 'MESH') {
      for (let i = 0; i < ids.length; i++) {
        for (let j = 0; j < ids.length; j++) {
          if (i !== j) {
            edges.push({ source: ids[i], target: ids[j], weight: 1 });
          }
        }
      }
    } else if (topo === 'UNCONSTRAINED' || topo === 'EMERGENT') {
      for (let i = 0; i < ids.length; i++) {
        for (let j = 0; j < ids.length; j++) {
          if (i !== j && (i + j) % 2 === 1) {
            edges.push({ source: ids[i], target: ids[j], weight: 1 });
          }
        }
      }
      if (ids.length >= 2) {
        edges.push({ source: ids[0], target: ids[1], weight: 2 });
        edges.push({ source: ids[1], target: ids[0], weight: 2 });
      }
    }
    return edges;
  };

  const getProviderColor = (p) => {
    switch ((p || '').toLowerCase()) {
      case 'ollama': return '#fbbf24';
      case 'aicredits': return '#38bdf8';
      case 'openai': return '#34d399';
      case 'groq': return '#fb923c';
      case 'gemini': return '#38bdf8';
      case 'mistral': return '#c084fc';
      default: return '#94a3b8';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header Deck */}
      <div>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Experiment Execution Deck
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Configure communication network topologies, inspect the 6-agent heterogeneous LLM team, and execute empirical deliberation trials.
        </p>
      </div>

      {errorMsg && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: 8,
            padding: '12px 16px',
            color: '#f87171',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 6-Model Agent Registry Rack */}
      <div
        className="card"
        style={{
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={18} color="var(--accent-star)" />
            <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Heterogeneous Multi-LLM Cluster (5 Cloud APIs + 1 Local Ollama)
            </h3>
          </div>
          <button
            type="button"
            onClick={fetchModelsData}
            disabled={loadingModels}
            className="btn btn-secondary"
            style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <RefreshCw size={12} className={loadingModels ? 'spin' : ''} />
            {loadingModels ? 'Polling Endpoints...' : 'Refresh Cluster Status'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
          {modelsConfig?.agents?.map((ag, idx) => {
            const statusInfo = modelsStatus?.agents?.find((s) => s.agent_id === ag.agent_id);
            const isOnline = ag.is_local ? (statusInfo?.reachable ?? false) : ag.has_api_key;
            const pColor = getProviderColor(ag.provider);

            return (
              <div
                key={ag.agent_id}
                className="bezel-screen"
                style={{
                  padding: '10px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  opacity: idx < numAgents ? 1 : 0.4,
                  border: ag.agent_id === 'agent_6' ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)' }}>
                    A{idx + 1}: {ag.role}
                  </span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 9,
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: `${pColor}22`,
                      color: pColor,
                      border: `1px solid ${pColor}44`,
                      textTransform: 'uppercase',
                    }}
                  >
                    {ag.provider} {ag.is_local ? '(LOCAL)' : ''}
                  </span>
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={ag.model}
                >
                  {ag.model}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
                  <span className={`led-indicator ${isOnline ? 'led-green' : (ag.is_local ? 'led-amber' : 'led-gray')}`} />
                  <span>{ag.is_local ? (statusInfo?.reachable ? 'Ollama Online' : 'Ollama Local') : (ag.has_api_key ? 'API Key Active' : 'Offline / Sim Mode')}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Control Deck Left, Telemetry Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: 24 }}>
        {/* Left Column: Configuration Controls */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border-color)', paddingBottom: 8 }}>
            1. Select Benchmark Task
          </h3>

          {/* Task Category Filter */}
          <div className="form-group">
            <label className="form-label">Task Category</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['ALL', 'Reasoning', 'Question Answering', 'Decision/Summary'].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(cat);
                    const matching = tasks.filter((t) => cat === 'ALL' || t.category === cat);
                    if (matching.length > 0) setSelectedTaskId(matching[0].id);
                  }}
                  className={`btn ${selectedCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: 12, padding: '5px 12px' }}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Task Selector Dropdown */}
          <div className="form-group">
            <label className="form-label">Task Selection</label>
            <select
              value={selectedTaskId}
              onChange={(e) => setSelectedTaskId(e.target.value)}
              className="form-select"
              disabled={loadingTasks || isRunning}
            >
              {filteredTasks.map((t) => (
                <option key={t.id} value={t.id}>
                  [{t.category}] {t.title} ({t.difficulty})
                </option>
              ))}
            </select>
          </div>

          {/* Selected Task Details Box */}
          {currentTask && (
            <div className="bezel-screen" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-star)' }}>{currentTask.title}</span>
                <span className="mono" style={{ fontSize: 11, background: 'var(--bg-card)', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-color)' }}>
                  {currentTask.difficulty}
                </span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                {currentTask.question}
              </p>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: 6 }}>
                <strong>Criteria:</strong> {currentTask.evaluation_criteria}
              </div>
            </div>
          )}

          <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border-color)', paddingBottom: 8, marginTop: 4 }}>
            2. Communication Topology
          </h3>

          {/* 4 Topology Physical Selector Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: 10 }}>
            {/* Star */}
            <div
              onClick={() => setSelectedTopology('STAR')}
              style={{
                border: `2px solid ${selectedTopology === 'STAR' ? '#38bdf8' : 'var(--border-color)'}`,
                background: selectedTopology === 'STAR' ? 'rgba(56, 189, 248, 0.12)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'STAR' ? '0 0 12px rgba(56, 189, 248, 0.25)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Sparkles size={18} color="#38bdf8" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 12, fontWeight: 700 }}>STAR</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                Central Hub
              </div>
            </div>

            {/* Chain */}
            <div
              onClick={() => setSelectedTopology('CHAIN')}
              style={{
                border: `2px solid ${selectedTopology === 'CHAIN' ? '#a855f7' : 'var(--border-color)'}`,
                background: selectedTopology === 'CHAIN' ? 'rgba(168, 85, 247, 0.12)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'CHAIN' ? '0 0 12px rgba(168, 85, 247, 0.25)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <GitCommit size={18} color="#a855f7" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 12, fontWeight: 700 }}>CHAIN</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                Sequential
              </div>
            </div>

            {/* Mesh */}
            <div
              onClick={() => setSelectedTopology('MESH')}
              style={{
                border: `2px solid ${selectedTopology === 'MESH' ? '#10b981' : 'var(--border-color)'}`,
                background: selectedTopology === 'MESH' ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'MESH' ? '0 0 12px rgba(16, 185, 129, 0.25)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Network size={18} color="#10b981" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 12, fontWeight: 700 }}>MESH</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                All-to-All
              </div>
            </div>

            {/* Emergent */}
            <div
              onClick={() => setSelectedTopology('UNCONSTRAINED')}
              style={{
                border: `2px solid ${selectedTopology === 'UNCONSTRAINED' ? '#f59e0b' : 'var(--border-color)'}`,
                background: selectedTopology === 'UNCONSTRAINED' ? 'rgba(245, 158, 11, 0.12)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'UNCONSTRAINED' ? '0 0 12px rgba(245, 158, 11, 0.25)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Activity size={18} color="#f59e0b" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 12, fontWeight: 700 }}>EMERGENT</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                Unconstrained
              </div>
            </div>
          </div>

          <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border-color)', paddingBottom: 8, marginTop: 4 }}>
            3. Cluster Parameters
          </h3>

          {/* Number of Agents */}
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <label className="form-label">Cluster Size</label>
              <span className="mono" style={{ fontSize: 12, color: '#38bdf8', fontWeight: 700 }}>{numAgents} Agents</span>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              {[4, 5, 6].map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => setNumAgents(count)}
                  className={`btn ${numAgents === count ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1, padding: '7px 0', fontSize: 12 }}
                  disabled={isRunning}
                >
                  <Users size={13} />
                  {count} Agents
                </button>
              ))}
            </div>
          </div>

          {/* Max Turns */}
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <label className="form-label">Max Deliberation Turns</label>
              <span className="mono" style={{ fontSize: 12, color: '#38bdf8', fontWeight: 700 }}>{maxTurns} Turns</span>
            </div>
            <input
              type="range"
              min="4"
              max="15"
              step="1"
              value={maxTurns}
              onChange={(e) => setMaxTurns(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
              disabled={isRunning}
            />
          </div>

          {/* Action Trigger Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 6 }}>
            <button
              onClick={handleRunSingle}
              disabled={isRunning || isBatchRunning || !selectedTaskId}
              className="btn btn-primary"
              style={{ padding: '12px 20px', fontSize: 14 }}
            >
              {isRunning ? (
                <>
                  <Loader2 size={18} className="spin" />
                  Deliberating Trial...
                </>
              ) : (
                <>
                  <PlayCircle size={18} />
                  Run Single Experiment ({selectedTopology})
                </>
              )}
            </button>

            <button
              onClick={() => handleRunBatchSweep(3)}
              disabled={isRunning || isBatchRunning || !selectedTaskId}
              className="btn btn-secondary"
              style={{ padding: '10px 16px', fontSize: 12 }}
            >
              {isBatchRunning ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Executing Sweep...
                </>
              ) : (
                <>
                  <Layers size={15} color="#a855f7" />
                  Run 4-Topology Sweep (Star + Chain + Mesh + Emergent × 3)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Live Radar Preview & Execution Monitor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Topology Preview */}
          <div className="card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Radio size={16} color="var(--accent-star)" />
                <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Topology Routing Graph
                </h3>
              </div>
              <TopologyBadge topology={selectedTopology} />
            </div>

            <TopologyVisualizer
              topology={selectedTopology}
              nodes={previewNodes}
              edges={getDynamicPreviewEdges(selectedTopology)}
              height={300}
              isPreview={true}
            />

            {/* Topology description rule note */}
            <div className="bezel-screen" style={{ marginTop: 12, padding: 12, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {selectedTopology === 'STAR' && (
                <div>
                  <strong style={{ color: 'var(--accent-star)' }}>Star Rule:</strong> Central Coordinator (A1) acts as the single central hub. Peripheral agents (A2 to A{numAgents}) can only communicate directly with the Coordinator. No lateral peer-to-peer messages are permitted.
                </div>
              )}
              {selectedTopology === 'CHAIN' && (
                <div>
                  <strong style={{ color: 'var(--accent-chain)' }}>Chain Rule:</strong> Sequential deterministic pipeline (A1 → A2 → ... → A{numAgents} → A1). Each agent only receives context from its predecessor and forwards findings to its successor.
                </div>
              )}
              {selectedTopology === 'MESH' && (
                <div>
                  <strong style={{ color: 'var(--accent-mesh)' }}>Mesh Rule:</strong> Fully interconnected network. All agents (A1 to A{numAgents}) are authorized to directly converse with any other agent across turn rounds.
                </div>
              )}
              {(selectedTopology === 'UNCONSTRAINED' || selectedTopology === 'EMERGENT') && (
                <div>
                  <strong style={{ color: 'var(--accent-emergent)' }}>Unconstrained / Emergent Rule:</strong> Dynamic self-organizing communication graph without static routing bottlenecks. Agents dynamically address peers or broadcast context organically based on communicative necessity.
                </div>
              )}
            </div>
          </div>

          {/* Live Execution Stream */}
          <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={15} color="var(--accent-star)" />
                <h3 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Execution Monitor
                </h3>
              </div>
              {isRunning && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#38bdf8' }}>
                  <Loader2 size={14} className="spin" />
                  <span className="mono">Deliberating...</span>
                </div>
              )}
            </div>

            {isBatchRunning && (
              <div className="bezel-screen" style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
                  <span>Batch Sweep Progress</span>
                  <span className="mono">{batchProgress.current} / {batchProgress.total} Trials</span>
                </div>
                <div style={{ width: '100%', height: 6, background: 'var(--bg-card)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${(batchProgress.current / (batchProgress.total || 1)) * 100}%`,
                      background: 'linear-gradient(90deg, #0284c7, #a855f7)',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              </div>
            )}

            <div
              className="bezel-screen"
              style={{
                flex: 1,
                minHeight: 160,
                padding: 12,
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              {executionLogs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 44 }}>
                  Awaiting trial command. Configure parameters and trigger execution.
                </div>
              ) : (
                executionLogs.map((log, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, color: i === executionLogs.length - 1 ? '#38bdf8' : 'var(--text-secondary)' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{log.time.toLocaleTimeString()}</span>
                    <span>›</span>
                    <span>{log.text}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
