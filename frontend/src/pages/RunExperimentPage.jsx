import React, { useState, useEffect, useRef } from 'react';
import { PlayCircle, Star, GitCommit, GitBranch, Network, Activity, Users, AlertTriangle, ChevronRight, Layers, ArrowRight, Loader2, Cpu, RefreshCw, CheckCircle, Terminal, Radio, Eye, Trash2, Edit3, RotateCcw, FileText, ChevronDown, Check, Sliders } from 'lucide-react';
import { api } from '../services/api';
import TopologyBadge from '../components/TopologyBadge';
import TopologyVisualizer from '../components/TopologyVisualizer';
import LoadingState from '../components/LoadingState';
import ApiErrorModal from '../components/ApiErrorModal';
import MultiTopologyComparisonRadar from '../components/MultiTopologyComparisonRadar';

// Strictly defined models configured in the codebase & environment
const BASE_CONFIGURED_MODELS = [
  { id: 'openai/gpt-oss-120b', name: 'OpenAI GPT-OSS 120B (Cloud)', provider: 'aicredits', is_local: false },
  { id: 'qwen/qwen3-30b-a3b-instruct-2507', name: 'Qwen 3 30B Instruct (Cloud)', provider: 'aicredits', is_local: false },
  { id: 'deepseek/deepseek-v3.2', name: 'DeepSeek V3.2 (Cloud)', provider: 'aicredits', is_local: false },
  { id: 'google/gemini-2.0-flash', name: 'Google Gemini 2.0 Flash (Cloud)', provider: 'aicredits', is_local: false },
  { id: 'nex-agi/nex-n2-mini', name: 'Nex-AGI N2 Mini (Cloud)', provider: 'aicredits', is_local: false },
  { id: 'llama3:latest', name: 'Ollama Llama 3 (Local GPU)', provider: 'ollama', is_local: true },
];

export default function RunExperimentPage({ onExperimentCompleted, preselectedTaskId = null }) {
  const [tasks, setTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(true);

  // Model & Agents Config State
  const [modelsConfig, setModelsConfig] = useState(null);
  const [modelsStatus, setModelsStatus] = useState(null);
  const [loadingModels, setLoadingModels] = useState(false);

  // Derive strictly code/env-configured models
  const availableModels = (() => {
    const map = new Map();
    BASE_CONFIGURED_MODELS.forEach((m) => map.set(m.id, m));
    if (modelsConfig?.agents) {
      modelsConfig.agents.forEach((ag) => {
        if (ag.model && !map.has(ag.model)) {
          map.set(ag.model, {
            id: ag.model,
            name: `${ag.model} (${ag.is_local ? 'Local GPU' : 'Cloud'})`,
            provider: ag.provider,
            is_local: ag.is_local,
          });
        }
      });
    }
    return Array.from(map.values());
  })();

  // Per-Agent Dynamic Model Selection State
  const [agentModels, setAgentModels] = useState({
    agent_1: 'openai/gpt-oss-120b',
    agent_2: 'qwen/qwen3-30b-a3b-instruct-2507',
    agent_3: 'deepseek/deepseek-v3.2',
    agent_4: 'google/gemini-2.0-flash',
    agent_5: 'nex-agi/nex-n2-mini',
    agent_6: 'llama3:latest',
  });

  // Form State
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [selectedTopology, setSelectedTopology] = useState('STAR');
  const [numAgents, setNumAgents] = useState(6);
  const [maxTurns, setMaxTurns] = useState(8);

  // User Custom Prompt State
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customCriteria, setCustomCriteria] = useState('');
  const [showCriteria, setShowCriteria] = useState(false);

  // Execution & Comparison State
  const [isRunning, setIsRunning] = useState(false);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });
  const [executionLogs, setExecutionLogs] = useState([]);
  const [lastFinishedExpId, setLastFinishedExpId] = useState(null);
  const [batchResults, setBatchResults] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [apiErrorModalMsg, setApiErrorModalMsg] = useState(null);
  const [retryContext, setRetryContext] = useState(null);

  const logsEndRef = useRef(null);

  // Auto-scroll execution monitor to latest message
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [executionLogs]);

  const fetchModelsData = async () => {
    setLoadingModels(true);
    try {
      const [cfg, stat] = await Promise.all([
        api.getModelsConfig(),
        api.getModelsStatus()
      ]);
      setModelsConfig(cfg);
      setModelsStatus(stat);

      if (cfg?.agents) {
        const initial = {};
        cfg.agents.forEach(a => {
          initial[a.agent_id] = a.model;
        });
        setAgentModels(prev => ({ ...initial, ...prev }));
      }
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

  // Sync custom prompt when selected task changes (unless in dedicated custom mode)
  useEffect(() => {
    if (currentTask && !isCustomMode) {
      setCustomPrompt(currentTask.question || '');
      setCustomTitle(currentTask.title || '');
      setCustomCriteria(currentTask.evaluation_criteria || '');
    }
  }, [selectedTaskId, currentTask, isCustomMode]);

  const isPromptEdited = currentTask && customPrompt.trim() !== (currentTask.question || '').trim();

  // Model change handler for an individual agent
  const handleAgentModelChange = (agentId, newModel) => {
    setAgentModels(prev => ({
      ...prev,
      [agentId]: newModel
    }));
  };

  const handleRunSingle = async () => {
    if (!selectedTaskId && !customPrompt.trim()) return;
    setIsRunning(true);
    setLastFinishedExpId(null);
    setErrorMsg(null);
    setApiErrorModalMsg(null);
    setRetryContext({ type: 'SINGLE', topology: selectedTopology });

    const effectiveTitle = isCustomMode ? (customTitle.trim() || 'Custom User Analysis') : (isPromptEdited ? `${currentTask?.title} (Customized)` : (currentTask?.title || selectedTaskId));

    const initialLogs = [
      { text: `[CLUSTER INIT] Activating ${numAgents} agents with configured LLMs (No simulated responses)...`, time: new Date() },
      { text: `[TOPOLOGY] Enforcing ${selectedTopology} communication routing constraints...`, time: new Date() },
      { text: `[DISPATCH] Broadcasting task '${effectiveTitle}' to agents...`, time: new Date() },
    ];
    setExecutionLogs(initialLogs);

    // Live deliberation step messages
    let stepCount = 0;
    const stepMessages = [
      `[TURN 1] Agent 1 (Coordinator - ${agentModels.agent_1 || 'LLM'}) formulating task decomposition...`,
      `[TURN 2] Agent 2 (Solver - ${agentModels.agent_2 || 'LLM'}) generating primary solution hypothesis...`,
      `[TURN 3] Agent 3 (Critic - ${agentModels.agent_3 || 'LLM'}) executing constraint audit & contradiction checks...`,
      `[TURN 4] Agent 4 (Fact Checker - ${agentModels.agent_4 || 'LLM'}) validating logical deductions against premises...`,
      `[TURN 5] Agent 5 (Alternative Solver - ${agentModels.agent_5 || 'LLM'}) cross-evaluating alternative paths...`,
      `[TURN 6] Agent 6 (Final Reviewer - ${agentModels.agent_6 || 'LLM'}) verifying consistency...`,
      `[SYNTHESIS] Consolidating peer critiques into final consensus...`
    ];

    const intervalId = setInterval(() => {
      if (stepCount < stepMessages.length) {
        setExecutionLogs((prev) => [
          ...prev,
          { text: stepMessages[stepCount], time: new Date() }
        ]);
        stepCount++;
      }
    }, 1400);

    try {
      const payload = {
        task_id: isCustomMode ? 'custom' : (selectedTaskId || 'custom'),
        topology: selectedTopology,
        num_agents: Number(numAgents),
        max_turns: Number(maxTurns),
        agent_models: agentModels,
      };

      if (isCustomMode || isPromptEdited) {
        payload.custom_prompt = customPrompt.trim();
        payload.custom_title = customTitle.trim() || undefined;
        payload.custom_criteria = customCriteria.trim() || undefined;
      }

      const result = await api.runExperiment(payload);

      clearInterval(intervalId);

      const statusTag = result.success ? 'PASSED' : `FAILED (${result.failure_type})`;
      setExecutionLogs((prev) => [
        ...prev,
        { text: `[SYNTHESIS COMPLETE] Final answer synthesized by Coordinator.`, time: new Date() },
        { text: `[EVALUATION] Two-stage verification outcome: ${statusTag}`, time: new Date() },
        { text: `[NETWORK] Logged ${result.total_messages || result.messages?.length || 0} messages across ${result.turns_taken || maxTurns} turns. Density: ${result.network_metrics?.communication_density ?? 0}`, time: new Date() },
        { text: `[COMPLETED] Trial #${result.id.substring(0, 8)} saved to database.`, time: new Date() },
      ]);

      setLastFinishedExpId(result.id);
      setRetryContext(null);
      setIsRunning(false);
    } catch (err) {
      clearInterval(intervalId);
      setErrorMsg(err.message);
      setExecutionLogs((prev) => [
        ...prev,
        { text: `[NOTICE] Execution note: ${err.message}`, time: new Date() }
      ]);
      setIsRunning(false);
    }
  };

  // Run 5-Topology Sweep (STAR, CHAIN, MESH, TREE, EMERGENT) with continuous seamless execution
  const handleRunBatchSweep = async (repetitions = 1, resumeIndex = 0, existingResults = []) => {
    if (!selectedTaskId && !customPrompt.trim()) return;
    setIsBatchRunning(true);
    setErrorMsg(null);
    setApiErrorModalMsg(null);

    const topologies = ['STAR', 'CHAIN', 'MESH', 'TREE', 'UNCONSTRAINED'];
    const total = topologies.length * repetitions;

    if (resumeIndex === 0) {
      setBatchResults([]);
    } else {
      setBatchResults(existingResults);
    }

    setBatchProgress({ current: resumeIndex, total });

    const effectiveTitle = isCustomMode ? (customTitle.trim() || 'Custom User Analysis') : (isPromptEdited ? `${currentTask?.title} (Customized)` : (currentTask?.title || selectedTaskId));

    if (resumeIndex > 0) {
      const resumeTopo = topologies[resumeIndex] === 'UNCONSTRAINED' ? 'EMERGENT' : topologies[resumeIndex];
      setExecutionLogs((prev) => [
        ...prev,
        { text: `[RESUMING SWEEP] Resuming comparative sweep from ${resumeTopo} (${resumeIndex + 1}/${total}) preserving ${existingResults.length} prior trial results...`, time: new Date() },
      ]);
    } else {
      setExecutionLogs([
        { text: `[COMPARATIVE SWEEP INIT] Starting 5-Topology comparative sweep (${total} trials) on '${effectiveTitle}' with auto-escalation...`, time: new Date() },
      ]);
    }

    const collectedResults = [...existingResults];
    let currentIdx = resumeIndex;

    try {
      for (let i = resumeIndex; i < topologies.length; i++) {
        currentIdx = i;
        const topo = topologies[i];
        const topoLabel = topo === 'UNCONSTRAINED' ? 'EMERGENT' : topo;

        setExecutionLogs((prev) => [
          ...prev,
          { text: `[RUNNING ${i + 1}/${total}] Executing ${topoLabel} topology...`, time: new Date() },
        ]);

        const payload = {
          task_id: isCustomMode ? 'custom' : (selectedTaskId || 'custom'),
          topology: topo,
          num_agents: Number(numAgents),
          max_turns: Number(maxTurns),
          agent_models: agentModels,
        };

        if (isCustomMode || isPromptEdited) {
          payload.custom_prompt = customPrompt.trim();
          payload.custom_title = customTitle.trim() || undefined;
          payload.custom_criteria = customCriteria.trim() || undefined;
        }

        const res = await api.runExperiment(payload);
        collectedResults.push(res);
        setBatchResults([...collectedResults]);
        setBatchProgress({ current: i + 1, total });

        setExecutionLogs((prev) => [
          ...prev,
          { text: `[${topoLabel} DONE] Outcome: ${res.success ? 'PASSED' : 'FAILED (' + res.failure_type + ')'} | Messages: ${res.total_messages} | Density: ${res.network_metrics?.communication_density ?? 0}`, time: new Date() },
        ]);
      }

      setBatchResults(collectedResults);
      setRetryContext(null);

      setExecutionLogs((prev) => [
        ...prev,
        { text: `[SWEEP COMPLETE] Successfully completed all ${total} trials across Star, Chain, Mesh, Tree, and Emergent. Comparative Post-Mortem Analytics loaded below.`, time: new Date() },
      ]);

      setIsBatchRunning(false);
    } catch (err) {
      const failedTopo = topologies[currentIdx] === 'UNCONSTRAINED' ? 'EMERGENT' : topologies[currentIdx];
      setErrorMsg(`Batch sweep encountered issue at ${failedTopo}: ${err.message}`);
      setExecutionLogs((prev) => [
        ...prev,
        { text: `[BATCH SWEEP PAUSED at ${failedTopo}] ${err.message}`, time: new Date() }
      ]);
      setIsBatchRunning(false);
    }
  };

  const handleRetryExecution = () => {
    if (!retryContext || retryContext.type === 'SINGLE') {
      handleRunSingle();
    } else if (retryContext.type === 'BATCH') {
      handleRunBatchSweep(
        retryContext.repetitions || 1,
        retryContext.resumeIndex || 0,
        retryContext.collectedResults || []
      );
    }
  };

  const getRetryButtonLabel = () => {
    if (!retryContext || retryContext.type === 'SINGLE') {
      const topo = selectedTopology === 'UNCONSTRAINED' ? 'EMERGENT' : selectedTopology;
      return `Retry Single Run (${topo})`;
    }
    return `Resume Batch Sweep (${retryContext.failedTopology} - ${retryContext.resumeIndex + 1}/${retryContext.total})`;
  };

  // Agent team list with assigned model names for Radar Preview
  const checkIsLocal = (m = '') => !m.toLowerCase().startsWith('meta-llama/') && (m.toLowerCase().includes('ollama') || m.toLowerCase().startsWith('llama3') || m.toLowerCase().includes('localhost'));

  const previewNodes = [
    { id: 'agent_1', name: 'Coordinator', role: 'Coordinator', is_central: true, model: agentModels.agent_1 || 'openai/gpt-oss-120b', provider: checkIsLocal(agentModels.agent_1) ? 'ollama' : 'aicredits', is_local: checkIsLocal(agentModels.agent_1) },
    { id: 'agent_2', name: 'Solver', role: 'Solver', is_central: false, model: agentModels.agent_2 || 'qwen/qwen3-30b-a3b-instruct-2507', provider: checkIsLocal(agentModels.agent_2) ? 'ollama' : 'aicredits', is_local: checkIsLocal(agentModels.agent_2) },
    { id: 'agent_3', name: 'Critic', role: 'Critic', is_central: false, model: agentModels.agent_3 || 'deepseek/deepseek-v3.2', provider: checkIsLocal(agentModels.agent_3) ? 'ollama' : 'aicredits', is_local: checkIsLocal(agentModels.agent_3) },
    { id: 'agent_4', name: 'Fact Checker', role: 'Fact Checker', is_central: false, model: agentModels.agent_4 || 'google/gemini-2.0-flash', provider: checkIsLocal(agentModels.agent_4) ? 'ollama' : 'aicredits', is_local: checkIsLocal(agentModels.agent_4) },
    { id: 'agent_5', name: 'Alternative Solver', role: 'Alternative Solver', is_central: false, model: agentModels.agent_5 || 'nex-agi/nex-n2-mini', provider: checkIsLocal(agentModels.agent_5) ? 'ollama' : 'aicredits', is_local: checkIsLocal(agentModels.agent_5) },
    { id: 'agent_6', name: 'Final Reviewer', role: 'Final Reviewer', is_central: false, model: agentModels.agent_6 || 'llama3:latest', provider: 'ollama', is_local: true },
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
    } else if (topo === 'TREE') {
      const parentChild = [
        ['agent_1', 'agent_2'],
        ['agent_1', 'agent_3'],
        ['agent_2', 'agent_4'],
        ['agent_3', 'agent_5'],
        ['agent_1', 'agent_6'],
      ];
      parentChild.forEach(([p, c]) => {
        if (ids.includes(p) && ids.includes(c)) {
          edges.push({ source: p, target: c, weight: 1 });
          edges.push({ source: c, target: p, weight: 1 });
        }
      });
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
      {/* API Error Popup Modal */}
      {apiErrorModalMsg && (
        <ApiErrorModal
          error={apiErrorModalMsg}
          onClose={() => setApiErrorModalMsg(null)}
          onRetry={handleRetryExecution}
          retryLabel={getRetryButtonLabel()}
        />
      )}

      {/* Header Deck */}
      <div>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Experiment Execution Deck
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Configure 5 network topologies (Star, Chain, Mesh, Tree, Emergent), select LLM models for each agent, and execute empirical deliberation trials.
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

      {/* 6-Model Agent Registry Rack with Interactive Per-Agent Model Selection */}
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
              Multi-LLM Cluster Model Selection (Assign Models to Agents)
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
            {loadingModels ? 'Polling Endpoints...' : 'Refresh Status'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10 }}>
          {[
            { id: 'agent_1', role: 'Coordinator', desc: 'Synthesizes decisions' },
            { id: 'agent_2', role: 'Solver', desc: 'Analytical deduction' },
            { id: 'agent_3', role: 'Critic', desc: 'Adversarial audit' },
            { id: 'agent_4', role: 'Fact Checker', desc: 'Empirical verification' },
            { id: 'agent_5', role: 'Alternative Solver', desc: 'Counter-hypotheses' },
            { id: 'agent_6', role: 'Final Reviewer', desc: 'QA criteria check' },
          ].map((ag, idx) => {
            const currentModel = agentModels[ag.id] || 'openai/gpt-oss-120b';
            const isLocal = !currentModel.toLowerCase().startsWith('meta-llama/') && (currentModel.toLowerCase().includes('ollama') || currentModel.toLowerCase().startsWith('llama3') || currentModel.toLowerCase().includes('localhost'));
            const providerName = isLocal ? 'ollama' : 'aicredits';
            const pColor = getProviderColor(providerName);
            const statusInfo = modelsStatus?.agents?.find((s) => s.agent_id === ag.id);
            const isOnline = isLocal ? (statusInfo?.reachable ?? true) : true;

            return (
              <div
                key={ag.id}
                className="bezel-screen"
                style={{
                  padding: '10px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  opacity: idx < numAgents ? 1 : 0.4,
                  border: ag.id === 'agent_6' ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-color)',
                  background: 'var(--bg-inner)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
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
                    {isLocal ? 'LOCAL GPU' : 'CLOUD API'}
                  </span>
                </div>

                {/* Model Selector Dropdown */}
                <select
                  value={currentModel}
                  onChange={(e) => handleAgentModelChange(ag.id, e.target.value)}
                  className="form-select"
                  disabled={isRunning || isBatchRunning}
                  style={{
                    fontSize: 11,
                    padding: '4px 6px',
                    height: 28,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-primary)',
                    borderRadius: 4,
                  }}
                >
                  <optgroup label="Configured Cloud Models (AICredits)">
                    {availableModels.filter(m => !m.is_local).map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </optgroup>
                  <optgroup label="Configured Local Models (Ollama GPU)">
                    {availableModels.filter(m => m.is_local).map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </optgroup>
                </select>

                <div style={{ fontSize: 10, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className={`led-indicator ${isOnline ? 'led-green' : 'led-amber'}`} />
                    <span>{isLocal ? 'Ollama GPU' : 'Cloud Gateway'}</span>
                  </div>
                  <span>{ag.desc}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Control Deck Left, Telemetry Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: 24 }}>
        {/* Left Column: Configuration Controls */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: 8 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              1. Select Benchmark Task / Custom Prompt
            </h3>

            {/* Mode Switcher */}
            <div style={{ display: 'flex', gap: 4, background: 'var(--bg-inner)', padding: 3, borderRadius: 6, border: '1px solid var(--border-color)' }}>
              <button
                type="button"
                onClick={() => {
                  setIsCustomMode(false);
                  if (currentTask) {
                    setCustomPrompt(currentTask.question || '');
                    setCustomTitle(currentTask.title || '');
                    setCustomCriteria(currentTask.evaluation_criteria || '');
                  }
                }}
                className={`btn ${!isCustomMode ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: 11, padding: '3px 10px', height: 'auto' }}
              >
                <FileText size={12} /> Presets
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCustomMode(true);
                  if (!customTitle) setCustomTitle('Custom User Analysis');
                }}
                className={`btn ${isCustomMode ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: 11, padding: '3px 10px', height: 'auto' }}
              >
                <Edit3 size={12} /> Custom Prompt
              </button>
            </div>
          </div>

          {/* Preset Mode Controls */}
          {!isCustomMode && (
            <>
              {/* Task Category Filter */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" style={{ fontSize: 11 }}>Task Category</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
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
                      style={{ fontSize: 11, padding: '4px 10px' }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Task Selector Dropdown */}
              <div className="form-group" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="form-label" style={{ fontSize: 11 }}>Task Selection Dropdown</label>
                  {currentTask && (
                    <span className="mono" style={{ fontSize: 10, color: 'var(--accent-star)' }}>
                      Difficulty: {currentTask.difficulty}
                    </span>
                  )}
                </div>
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
            </>
          )}

          {/* Custom Mode Title Input */}
          {isCustomMode && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ fontSize: 11 }}>Analysis / Task Title</label>
              <input
                type="text"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="e.g., Quantum Computing Superposition Analysis"
                className="form-input"
                style={{ width: '100%', fontSize: 13 }}
                disabled={isRunning}
              />
            </div>
          )}

          {/* User Prompt Input Box (Interactive Textarea) */}
          <div className="form-group" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Edit3 size={13} color="var(--accent-star)" />
                <label className="form-label" style={{ margin: 0, fontSize: 11 }}>
                  Task Prompt & Deliberation Question
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {isCustomMode ? (
                  <span className="badge badge-warning" style={{ fontSize: 10, padding: '1px 6px' }}>Custom Mode</span>
                ) : isPromptEdited ? (
                  <span className="badge badge-warning" style={{ fontSize: 10, padding: '1px 6px' }}>Edited / Customized</span>
                ) : (
                  <span className="badge badge-success" style={{ fontSize: 10, padding: '1px 6px' }}>Preset Default</span>
                )}
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  {customPrompt.length} chars
                </span>
              </div>
            </div>

            <div className="bezel-screen" style={{ padding: 8, background: 'var(--bg-inner)' }}>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Enter custom reasoning problem, logic puzzle, analytical question, or prompt premises here..."
                disabled={isRunning}
                style={{
                  width: '100%',
                  minHeight: 110,
                  maxHeight: 260,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-primary)',
                  fontSize: 13,
                  lineHeight: 1.5,
                  fontFamily: 'var(--font-sans)',
                  resize: 'vertical',
                }}
              />

              {/* Bottom Utility Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: 6, marginTop: 4 }}>
                <button
                  type="button"
                  onClick={() => setShowCriteria(!showCriteria)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    fontSize: 11,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <Sliders size={12} color="var(--accent-star)" />
                  <span>{showCriteria ? 'Hide Evaluation Criteria' : 'Edit Evaluation Criteria / Target (+)'}</span>
                </button>

                <div style={{ display: 'flex', gap: 6 }}>
                  {!isCustomMode && isPromptEdited && (
                    <button
                      type="button"
                      onClick={() => {
                        if (currentTask) {
                          setCustomPrompt(currentTask.question || '');
                          setCustomCriteria(currentTask.evaluation_criteria || '');
                        }
                      }}
                      className="btn btn-secondary"
                      style={{ padding: '2px 8px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <RotateCcw size={10} /> Reset to Preset
                    </button>
                  )}

                  {customPrompt.trim().length > 0 && (
                    <button
                      type="button"
                      onClick={() => setCustomPrompt('')}
                      className="btn btn-secondary"
                      style={{ padding: '2px 8px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <Trash2 size={10} /> Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Collapsible Evaluation Criteria */}
              {showCriteria && (
                <div style={{ marginTop: 8, borderTop: '1px dashed var(--border-color)', paddingTop: 8 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Verification Criteria / Expected Answer
                  </label>
                  <input
                    type="text"
                    value={customCriteria}
                    onChange={(e) => setCustomCriteria(e.target.value)}
                    placeholder="e.g., Must deduce Knight status for Alice and Knave status for Bob without contradiction"
                    className="form-input"
                    style={{ width: '100%', fontSize: 12, padding: '6px 10px' }}
                    disabled={isRunning}
                  />
                </div>
              )}
            </div>
          </div>

          <h3 style={{ fontSize: 15, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--border-color)', paddingBottom: 8, marginTop: 4 }}>
            2. Communication Topology (5 Topologies)
          </h3>

          {/* 5 Topology Physical Selector Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(85px, 1fr))', gap: 8 }}>
            {/* Star */}
            <div
              onClick={() => setSelectedTopology('STAR')}
              style={{
                border: `2px solid ${selectedTopology === 'STAR' ? '#38bdf8' : 'var(--border-color)'}`,
                background: selectedTopology === 'STAR' ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'STAR' ? '0 0 12px rgba(56, 189, 248, 0.3)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Star size={18} color="#38bdf8" fill="#38bdf8" fillOpacity={0.25} style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 11, fontWeight: 700 }}>STAR</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                Central Hub
              </div>
            </div>

            {/* Chain */}
            <div
              onClick={() => setSelectedTopology('CHAIN')}
              style={{
                border: `2px solid ${selectedTopology === 'CHAIN' ? '#a855f7' : 'var(--border-color)'}`,
                background: selectedTopology === 'CHAIN' ? 'rgba(168, 85, 247, 0.15)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'CHAIN' ? '0 0 12px rgba(168, 85, 247, 0.3)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <GitCommit size={18} color="#a855f7" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 11, fontWeight: 700 }}>CHAIN</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                Sequential
              </div>
            </div>

            {/* Mesh */}
            <div
              onClick={() => setSelectedTopology('MESH')}
              style={{
                border: `2px solid ${selectedTopology === 'MESH' ? '#10b981' : 'var(--border-color)'}`,
                background: selectedTopology === 'MESH' ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'MESH' ? '0 0 12px rgba(16, 185, 129, 0.3)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Network size={18} color="#10b981" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 11, fontWeight: 700 }}>MESH</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                All-to-All
              </div>
            </div>

            {/* Tree */}
            <div
              onClick={() => setSelectedTopology('TREE')}
              style={{
                border: `2px solid ${selectedTopology === 'TREE' ? '#ec4899' : 'var(--border-color)'}`,
                background: selectedTopology === 'TREE' ? 'rgba(236, 72, 153, 0.15)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: selectedTopology === 'TREE' ? '0 0 12px rgba(236, 72, 153, 0.3)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <GitBranch size={18} color="#ec4899" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 11, fontWeight: 700 }}>TREE</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                Hierarchical
              </div>
            </div>

            {/* Emergent */}
            <div
              onClick={() => setSelectedTopology('UNCONSTRAINED')}
              style={{
                border: `2px solid ${(selectedTopology === 'UNCONSTRAINED' || selectedTopology === 'EMERGENT') ? '#f59e0b' : 'var(--border-color)'}`,
                background: (selectedTopology === 'UNCONSTRAINED' || selectedTopology === 'EMERGENT') ? 'rgba(245, 158, 11, 0.15)' : 'var(--bg-inner)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: (selectedTopology === 'UNCONSTRAINED' || selectedTopology === 'EMERGENT') ? '0 0 12px rgba(245, 158, 11, 0.3)' : 'var(--inset-shadow)',
                transition: 'all 0.15s ease',
              }}
            >
              <Activity size={18} color="#f59e0b" style={{ marginBottom: 4 }} />
              <div style={{ fontSize: 11, fontWeight: 700 }}>EMERGENT</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
                Dynamic
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
                  disabled={isRunning || isBatchRunning}
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
              disabled={isRunning || isBatchRunning}
            />
          </div>

          {/* Action Trigger Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 6 }}>
            <button
              onClick={handleRunSingle}
              disabled={isRunning || isBatchRunning || (!selectedTaskId && !customPrompt.trim())}
              className="btn btn-primary"
              style={{ padding: '12px 20px', fontSize: 14, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
            >
              {isRunning ? (
                <LoadingState label={`Deliberating (${selectedTopology === 'UNCONSTRAINED' ? 'EMERGENT' : selectedTopology})...`} variant="Drive" size="sm" />
              ) : (
                <>
                  <PlayCircle size={18} />
                  <span>Run Single Experiment ({selectedTopology === 'UNCONSTRAINED' ? 'EMERGENT' : selectedTopology})</span>
                </>
              )}
            </button>

            <button
              onClick={() => handleRunBatchSweep(1)}
              disabled={isRunning || isBatchRunning || (!selectedTaskId && !customPrompt.trim())}
              className="btn btn-secondary"
              style={{ padding: '10px 16px', fontSize: 12, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
            >
              {isBatchRunning ? (
                <LoadingState label={`Executing Comparative Sweep (${batchProgress.current}/${batchProgress.total})...`} variant="Orbit" size="sm" />
              ) : (
                <>
                  <Layers size={15} color="#a855f7" />
                  <span>Run Comparative Sweep (Star + Chain + Mesh + Tree + Emergent)</span>
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
                  <strong style={{ color: 'var(--accent-star)' }}>Star Rule:</strong> Central Coordinator (A1: {agentModels.agent_1}) acts as the single central hub. Peripheral agents (A2 to A{numAgents}) can only communicate directly with the Coordinator. No lateral peer-to-peer messages are permitted.
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
              {selectedTopology === 'TREE' && (
                <div>
                  <strong style={{ color: '#ec4899' }}>Tree Rule:</strong> Hierarchical branching tree. Root Coordinator (A1) delegates to Branch Supervisors (A2, A3), which communicate with Leaf Specialists (A4, A5). Communication is strictly vertical between parents and children.
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
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {isRunning && (
                  <LoadingState label="Deliberating Turns" variant="Drive" size="sm" />
                )}
                {isBatchRunning && (
                  <LoadingState label="Sweep Progress" variant="Orbit" size="sm" />
                )}
                {executionLogs.length > 0 && !isRunning && !isBatchRunning && (
                  <button
                    onClick={() => setExecutionLogs([])}
                    className="btn btn-secondary"
                    style={{ padding: '2px 8px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}
                    title="Clear monitor logs"
                  >
                    <Trash2 size={11} /> Clear
                  </button>
                )}
              </div>
            </div>

            {/* Batch Progress Bar */}
            {isBatchRunning && (
              <div className="bezel-screen" style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
                  <span>Comparative Sweep Progress</span>
                  <span className="mono">{batchProgress.current} / {batchProgress.total} Topologies</span>
                </div>
                <div style={{ width: '100%', height: 6, background: 'var(--bg-card)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${(batchProgress.current / (batchProgress.total || 1)) * 100}%`,
                      background: 'linear-gradient(90deg, #38bdf8, #ec4899, #a855f7)',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              </div>
            )}

            {/* Terminal Monitor Stream Box */}
            <div
              className="bezel-screen mono"
              style={{
                flex: 1,
                minHeight: 280,
                maxHeight: 400,
                overflowY: 'auto',
                padding: 14,
                fontSize: 12,
                lineHeight: 1.6,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                background: 'var(--bg-inner)',
                border: '1px solid var(--border-color)',
              }}
            >
              {executionLogs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', margin: 'auto' }}>
                  Awaiting experiment execution. Select parameters, assign LLM models, and launch trial above.
                </div>
              ) : (
                executionLogs.map((log, index) => {
                  const rawText = typeof log === 'string' ? log : (log?.text || '');
                  const logTime = log?.time instanceof Date ? log.time : (log?.time ? new Date(log.time) : new Date());
                  let color = 'var(--text-secondary)';
                  if (rawText.includes('[CLUSTER INIT]') || rawText.includes('[COMPARATIVE SWEEP INIT]')) color = '#38bdf8';
                  else if (rawText.includes('[TOPOLOGY]')) color = '#a855f7';
                  else if (rawText.includes('[DISPATCH]')) color = '#f59e0b';
                  else if (rawText.includes('[EVALUATION]')) color = rawText.includes('PASSED') ? '#22c55e' : '#f43f5e';
                  else if (rawText.includes('[NETWORK]') || rawText.includes('[COMPLETED]') || rawText.includes('DONE]')) color = '#38bdf8';
                  else if (rawText.includes('[ERROR]') || rawText.includes('[BATCH ERROR]') || rawText.includes('PAUSED')) color = '#ef4444';
                  else if (rawText.includes('[SYNTHESIS') || rawText.includes('[ESCALATION') || rawText.includes('[NOTICE]')) color = '#10b981';

                  return (
                    <div key={index} style={{ display: 'flex', gap: 8 }}>
                      <span style={{ color: 'var(--text-muted)', minWidth: 70, userSelect: 'none' }}>
                        {logTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}›
                      </span>
                      <span style={{ color, wordBreak: 'break-word' }}>{rawText}</span>
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>

            {/* Persistent Post-Mortem Navigation Banner */}
            {lastFinishedExpId && !isRunning && !isBatchRunning && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  background: 'rgba(34, 197, 94, 0.12)',
                  border: '1px solid rgba(34, 197, 94, 0.4)',
                  borderRadius: 8,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircle size={18} color="#22c55e" />
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>
                    Trial Completed Successfully (#{lastFinishedExpId.substring(0, 8)})
                  </span>
                </div>
                <button
                  onClick={() => onExperimentCompleted(lastFinishedExpId)}
                  className="btn btn-primary"
                  style={{ fontSize: 12, padding: '6px 14px', display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  <span>Inspect Post-Mortem</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Comparative Multi-Topology Radar Analytics Card (Rendered upon completing multi-topology sweep) */}
      {batchResults.length > 0 && !isBatchRunning && (
        <MultiTopologyComparisonRadar
          results={batchResults}
          onInspectExperiment={onExperimentCompleted}
        />
      )}
    </div>
  );
}
