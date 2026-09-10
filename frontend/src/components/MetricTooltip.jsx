import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircle, Info, Sparkles, BookOpen } from 'lucide-react';

export const METRIC_DEFINITIONS = {
  accuracy: {
    name: 'Accuracy [Wilson 95% CI]',
    category: 'Performance Benchmark',
    formula: 'p̂ ± z · √[p̂(1 - p̂)/n + z²/(4n²)] / (1 + z²/n)',
    summary: 'Proportion of tasks solved correctly, bounded by an asymmetric 95% Wilson score confidence interval.',
    interpretation: 'Wilson bounds account for sample size variance and avoid zero-variance boundary artifacts when accuracy is 0% or 100% in small cohorts (N < 30).'
  },
  failure_rate: {
    name: 'Failure Rate',
    category: 'Error Taxonomy',
    formula: '(Failed Trials / Total Runs) × 100%',
    summary: 'Percentage of benchmark trials where the agent ensemble failed to reach the correct answer or violated constraints.',
    interpretation: 'Lower is better. Classified into Wrong Final Answer, Hallucination, Contradiction, Premature Agreement, or Information Loss.'
  },
  density: {
    name: 'Communication Density',
    category: 'Network Topology',
    formula: 'D = |E| / [|V| · (|V| - 1)]',
    summary: 'Ratio of observed directed message channels to the maximum possible pairwise channels.',
    interpretation: 'Ranges from 0 (isolated agents) to 1.0 (fully connected Mesh). High density fosters cross-verification but incurs O(N²) token overhead.'
  },
  betweenness: {
    name: 'Betweenness Centrality (CB)',
    category: 'Network Centrality',
    formula: 'CB(v) = ∑_{s≠v≠t} [σ_st(v) / σ_st]',
    summary: 'Fraction of all shortest communication paths that pass through this particular agent.',
    interpretation: 'High betweenness indicates an indispensable information gatekeeper or potential bottleneck (e.g. Star supervisor, Tree root).'
  },
  closeness: {
    name: 'Closeness Centrality (CC)',
    category: 'Network Centrality',
    formula: 'CC(v) = (N - 1) / ∑_{u≠v} d(v, u)',
    summary: 'Reciprocal of the average shortest path distance from an agent to all other agents in the graph.',
    interpretation: 'Higher closeness signifies that the agent can broadcast instructions and receive peer consensus rapidly with minimal intermediate hops.'
  },
  reciprocity: {
    name: 'Graph Reciprocity (r)',
    category: 'Network Topology',
    formula: 'r = |E_mutual| / |E|',
    summary: 'Proportion of directed communication links that are mutual and bidirectional.',
    interpretation: 'High reciprocity indicates bilateral consensus checking, debate, and peer review. Low reciprocity indicates one-way command pipelines.'
  },
  clustering: {
    name: 'Clustering Coefficient (C)',
    category: 'Network Topology',
    formula: 'C(v) = 2 · e_v / [k_v · (k_v - 1)]',
    summary: 'Probability that two distinct conversational partners of an agent also communicate directly with each other.',
    interpretation: 'High clustering reveals tightly-knit specialist sub-teams and localized triadic consensus loops.'
  },
  gini: {
    name: 'Message Gini Coefficient (G)',
    category: 'Message Distribution',
    formula: 'G = ∑_i ∑_j |m_i - m_j| / [2 · N² · μ]',
    summary: 'Quantifies conversational inequality and message concentration across the agent ensemble (0 to 1).',
    interpretation: '0.00 = perfectly egalitarian distribution (all agents speak equally); 1.00 = extreme bottleneck (one agent monopolizes all turns).'
  },
  entropy: {
    name: 'Shannon Message Entropy (H)',
    category: 'Information Theory',
    formula: 'H = - ∑_{i=1}^N p_i · log₂(p_i)',
    summary: 'Measures the information dispersion and conversational turn unpredictability across agents in bits.',
    interpretation: 'Maximized at log₂(N) when message volume is uniformly distributed. Plummets towards 0 when a single agent dominates dialogue.'
  },
  messages: {
    name: 'Average Message Volume',
    category: 'Communication Overhead',
    formula: '∑ messages / Total Trials',
    summary: 'Average number of discrete conversational exchanges and reasoning turns required to complete a task.',
    interpretation: 'Reflects coordination overhead and token consumption. High message counts without accuracy gains indicate debate looping.'
  },
  primary_failure: {
    name: 'Primary Failure Mode',
    category: 'Error Taxonomy',
    formula: 'argmax_k [Count(Failure_k)]',
    summary: 'The most dominant classification of error observed for this specific communication topology.',
    interpretation: 'Identifies structural weaknesses (e.g. Star tends toward Coordinator Hallucination, Chain suffers from Information Loss, Mesh from Premature Agreement).'
  },
  chi_square: {
    name: "Chi-Square Test of Independence (X²)",
    category: 'Statistical Hypothesis Testing',
    formula: 'X² = ∑_i ∑_j [(O_ij - E_ij)² / E_ij]',
    summary: 'Tests the null hypothesis (H₀) that failure mode frequency is independent of the multi-agent topology.',
    interpretation: 'A large X² with p < 0.05 rejects H₀, demonstrating that communication structure causally alters how multi-agent teams fail.'
  },
  p_value: {
    name: 'p-value',
    category: 'Statistical Hypothesis Testing',
    formula: 'P(X² ≥ observed | H₀)',
    summary: 'Probability of obtaining results at least as extreme as observed, assuming topology has no effect on failure modes.',
    interpretation: 'p < 0.05 is the academic benchmark for statistical significance, confirming observable differences are not random noise.'
  },
  cramers_v: {
    name: "Cramér's V (Effect Size)",
    category: 'Statistical Hypothesis Testing',
    formula: 'V = √[X² / (N · (min(r, c) - 1))]',
    summary: 'Standardized measure of association strength between categorical variables (0 = no association, 1 = complete association).',
    interpretation: '< 0.10: Negligible effect; 0.10 - 0.30: Small effect; 0.30 - 0.50: Medium effect; > 0.50: Large practical effect size.'
  },
  df: {
    name: 'Degrees of Freedom (df)',
    category: 'Statistical Hypothesis Testing',
    formula: 'df = (Rows - 1) × (Cols - 1)',
    summary: 'Number of independent categorical frequencies that are free to vary in the contingency table.',
    interpretation: 'Determines the exact shape of the reference Chi-Square distribution curve used to compute the p-value.'
  },
  sample_size: {
    name: 'Sample Size (N)',
    category: 'Statistical Rigor',
    formula: 'Total Evaluated Trials',
    summary: 'Total count of independent multi-agent benchmark trials included in the analysis.',
    interpretation: 'Higher sample sizes narrow the Wilson confidence intervals and increase the statistical power to detect subtle topology effects.'
  },
  degree: {
    name: 'Degree Centrality (In / Out)',
    category: 'Node Diagnostics',
    formula: 'k = k_in + k_out',
    summary: 'Total number of active directed connections to other agents in the communication network.',
    interpretation: 'In-degree measures peers listened to / received from; Out-degree measures instructions and answers sent.'
  },
  diameter: {
    name: 'Network Diameter',
    category: 'Network Topology',
    formula: 'max_{u,v} d(u, v)',
    summary: 'The longest shortest communication path between any two agents in the network.',
    interpretation: 'Represents worst-case information transmission latency across the mesh in communication hops.'
  },
  latency: {
    name: 'Execution Latency',
    category: 'System Performance',
    formula: 't_completion - t_start',
    summary: 'Total elapsed wall-clock time from task dispatch to final validated consensus.',
    interpretation: 'Dependent on model inference speeds, network roundtrips, and concurrency (parallel actors vs sequential chains).'
  },
  tokens: {
    name: 'Token Usage',
    category: 'Cost & Efficiency',
    formula: 'Prompt Tokens + Completion Tokens',
    summary: 'Cumulative language model tokens consumed across all agent prompts and completions during the trial.',
    interpretation: 'Directly dictates LLM API costs and identifies whether a topology suffers from token bloat.'
  }
};

export default function MetricTooltip({
  metric,
  customTitle,
  customFormula,
  customSummary,
  customDetails,
  children,
  showIcon = false,
  placement = 'top',
  className = '',
  style = {}
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef(null);

  const def = (metric && METRIC_DEFINITIONS[metric.toLowerCase()]) || {};
  const title = customTitle || def.name || metric || 'Metric Info';
  const category = def.category || 'Metric';
  const formula = customFormula || def.formula;
  const summary = customSummary || def.summary || 'Statistical measure for multi-agent evaluation.';
  const interpretation = customDetails || def.interpretation;

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 300;
    const tooltipHeight = 180; // approximate estimation
    const margin = 10;

    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    // Boundary collision checks on X axis
    if (left < margin) left = margin;
    if (left + tooltipWidth > window.innerWidth - margin) {
      left = window.innerWidth - tooltipWidth - margin;
    }

    let top = rect.top - tooltipHeight - margin;
    // If overflowing top boundary, place below the trigger
    if (top < margin || placement === 'bottom') {
      top = rect.bottom + margin;
    }

    setCoords({ top, left });
  };

  const handleMouseEnter = () => {
    updatePosition();
    setIsVisible(true);
  };

  const handleMouseLeave = () => {
    setIsVisible(false);
  };

  return (
    <span
      ref={triggerRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`metric-tooltip-trigger ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        cursor: 'help',
        borderBottom: children ? '1px dotted rgba(56, 189, 248, 0.5)' : 'none',
        transition: 'color 0.15s ease, border-color 0.15s ease',
        ...style
      }}
    >
      {children}
      {showIcon && (
        <HelpCircle
          size={12}
          color="var(--accent-star)"
          style={{ opacity: 0.75, flexShrink: 0 }}
        />
      )}

      {isVisible &&
        createPortal(
          <div
            className="metric-tooltip-card"
            style={{
              position: 'fixed',
              top: coords.top,
              left: coords.left,
              width: 300,
              zIndex: 999999,
              background: '#0e1422',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: 8,
              boxShadow: '0 12px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(56, 189, 248, 0.12)',
              padding: '12px 14px',
              color: '#f1f5f9',
              fontFamily: 'var(--font-sans, system-ui, sans-serif)',
              fontSize: 12,
              lineHeight: 1.45,
              pointerEvents: 'none',
              animation: 'fadeIn 0.15s ease-out'
            }}
          >
            {/* Category Banner */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 800,
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--accent-star, #38bdf8)',
                  background: 'rgba(56, 189, 248, 0.1)',
                  padding: '2px 6px',
                  borderRadius: 4
                }}
              >
                {category}
              </span>
              <BookOpen size={11} color="var(--text-muted, #64748b)" />
            </div>

            {/* Title */}
            <div style={{ fontWeight: 700, fontSize: 13, color: '#ffffff', marginBottom: 6 }}>
              {title}
            </div>

            {/* Formula box if available */}
            {formula && (
              <div
                style={{
                  background: '#070b12',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: 11,
                  color: '#38bdf8',
                  marginBottom: 8,
                  wordBreak: 'break-word'
                }}
              >
                {formula}
              </div>
            )}

            {/* Plain English Summary */}
            <div style={{ color: '#cbd5e1', marginBottom: 6 }}>
              {summary}
            </div>

            {/* Interpretation */}
            {interpretation && (
              <div
                style={{
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                  paddingTop: 6,
                  fontSize: 11,
                  color: '#94a3b8',
                  lineHeight: 1.4
                }}
              >
                <strong style={{ color: '#e2e8f0' }}>Interpretation: </strong>
                {interpretation}
              </div>
            )}
          </div>,
          document.body
        )}
    </span>
  );
}
