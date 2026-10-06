# AgentMesh Empirical Experimental Results

This directory contains the complete empirical dataset, analytical summaries, figures, and execution traces from the 175-run benchmark study evaluated across 5 communication topologies and 7 prompt families.

---

## 📊 Summary of Benchmark Results

Evaluated on a heterogeneous multi-LLM team (`llama3:8b`, `mistral:7b`, `phi3:medium`, `deepseek-r1:7b`) with 35 independent trials per topology.

| Topology | Runs | Accuracy (%) | 95% Confidence Interval | Mean Tokens | Mean Cost (USD) | Mean Latency (s) | Betweenness ($\mathcal{C}_B$) | Density ($D$) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tree** | 35 | **31.43%** | [16.05%, 46.81%] | 14,456 | $0.0024 | 116.91s | 0.095 | 0.057 |
| **Emergent** | 35 | **28.57%** | [13.60%, 43.54%] | 19,945 | $0.0043 | 117.98s | 0.060 | 0.062 |
| **Star** | 35 | **22.86%** | [8.95%, 36.77%] | 16,623 | $0.0023 | 115.30s | 0.086 | 0.034 |
| **Mesh** | 35 | **20.00%** | [6.75%, 33.25%] | 12,687 | $0.0032 | 119.91s | 0.071 | 0.086 |
| **Chain** | 35 | **17.14%** | [4.66%, 29.63%] | 12,679 | $0.0033 | 118.12s | 0.071 | 0.036 |

### Key Empirical Findings:
1. **Tree topology dominates**: Outperforms all topologies by up to 14.3 percentage points while maintaining near-lowest cost per task ($0.0024). Sub-problem decomposition and branch isolation prevent context pollution.
2. **Mesh density paradox**: Despite $O(N^2)$ connectivity and maximal graph density ($D = 0.086$), Mesh underperforms Tree by 11.4 percentage points, refuting the intuition that maximal inter-agent chatter improves reasoning.
3. **Information Attenuation in Chain**: Sequential pipeline achieves the lowest accuracy (17.14%) due to unrecoverable multi-hop semantic degradation.
4. **SNA Negative Correlation**: Total message count negatively correlates with task success ($r = -0.602, p < 0.0001$), demonstrating that high-performing teams communicate concisely while failing teams enter circular deliberation loops.

---

## 📁 Directory Structure & File Manifest

```
results/
├── README.md                     # This file: dataset documentation and guide
├── experiment_results.csv        # Primary tabular dataset (175 runs, 27 features)
├── statistical_summary.json      # Structured JSON metrics, CIs, and Pearson correlation matrices
├── paper_results_section.md      # Publication draft text and formatted LaTeX tables
├── traces.jsonl                  # Comprehensive raw LLM execution traces (2.1 MB)
├── figures/                      # High-resolution publication figures (300 DPI)
│   ├── fig1_accuracy_by_topology_and_model.png
│   ├── fig2_failure_signatures_heatmap.png
│   ├── fig3_failure_distribution_by_topology.png
│   ├── fig4_sna_correlation_matrix.png
│   ├── fig5_model_robustness_interaction.png
│   └── fig6_cost_accuracy_pareto.png
├── partitions/                   # Chunked partition runs (results_p01_p07.csv, traces_p01_p07.jsonl)
└── transcripts/                  # 175 markdown deliberation transcripts with per-turn agent dialogues
```

---

## 📋 Data Dictionary (`experiment_results.csv`)

| Column | Type | Description |
|:---|:---|:---|
| `timestamp` | ISO-8601 | Experiment completion timestamp |
| `prompt_id` | String | Unique prompt ID (e.g., `FC1_1.1_001` to `FC1_1.1_007`) |
| `prompt_family` | String | Benchmark failure category name |
| `failure_category`| String | Category code (`FC1` Specification, `FC2` Coordination, etc.) |
| `topology` | Enum | `STAR`, `CHAIN`, `TREE`, `MESH`, `EMERGENT` |
| `model` | String | LLM configuration (`heterogeneous`) |
| `replicate_id` | Int | Run replicate (1 to 5) |
| `success` | Int | Binary task success (1 = Pass, 0 = Fail) |
| `failure_mode` | String | Diagnosed MAST failure code (`FM-1.1`, `FM-1.3`, `FM-1.4`, `FM-1.5`, or `None`) |
| `total_messages` | Int | Total number of messages exchanged across all turns |
| `input_tokens` | Int | Total prompt tokens consumed |
| `output_tokens` | Int | Total generation tokens consumed |
| `total_tokens` | Int | `input_tokens + output_tokens` |
| `cost_usd` | Float | Calculated API / resource cost in USD |
| `latency_sec` | Float | End-to-end task execution wall-clock time in seconds |
| `graph_density` | Float | Network graph density $D \in [0, 1]$ |
| `coordinator_betweenness` | Float | Hub / Coordinator normalized betweenness centrality $\mathcal{C}_B \in [0, 1]$ |
| `reciprocity` | Float | Directed graph reciprocity $\mathcal{R} \in [0, 1]$ |
| `dissent_ratio` | Float | Fraction of turns exhibiting critical objection or disagreement |
| `clarification_rate`| Float | Fraction of turns requesting specification clarification |
| `lexical_decay_rate`| Float | Semantic drift rate across successive reasoning hops |
| `step_repetition_index`| Float | Frequency of repeated claims or circular arguments |
| `coordinator_dominance`| Float | Proportion of total communication volume occupied by the coordinator |
| `participation_entropy`| Float | Normalized Shannon entropy of message volume across agent roles |
| `failure_diagnosis` | String | Evaluator textual rationale for classification |
| `final_answer_snippet` | String | Synthesized answer returned to the user |

---

## 🔬 How to Replicate and Re-Analyze

### Re-generate Statistical Summary and Figures
```bash
# From workspace root:
python analysis/analyze_results.py --input results/experiment_results.csv --output results/
```

### Run Custom Subsets of the Benchmark
```bash
# Windows
run_experiments.bat 1 7

# Linux / macOS
chmod +x run_experiments.sh
./run_experiments.sh 1 7
```
