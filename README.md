# AgentMesh: Communication Topology as a First-Class Architectural Variable in Multi-Agent LLM Systems 🔬🌐

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2%2B-2496ED.svg)](https://docs.docker.com/compose/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-3.7-231F20.svg)](https://kafka.apache.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/React%2018-Vite%205-61DAFB.svg)](https://vitejs.dev/)

> **Conference Research Repository & Empirical Benchmark Artifact Suite**  
> An open-source research platform and empirical benchmark evaluating how communication topology, graph centrality, and asynchronous message streaming govern multi-agent LLM reasoning fidelity, failure modes, and communication costs.

---

## 📌 Abstract

Multi-agent large language model (LLM) architectures frequently treat communication structure as an implicit implementation detail rather than an explicit architectural design variable. We present **AgentMesh**, a systematic investigation demonstrating that communication topology exerts a first-order influence on collective multi-agent reasoning outcomes. 

Through an empirical evaluation of **175 runs** across 5 distinct communication topologies (**Tree**, **Emergent/Dynamic**, **Star**, **Mesh**, and **Chain**) using a heterogeneous multi-LLM team (`llama3:8b`, `mistral:7b`, `phi3:medium`, `deepseek-r1:7b`), we quantify topological sensitivity, social network centrality correlations, and failure signatures. Furthermore, we implement and benchmark a horizontally distributed, partitioned event-driven stream topology utilizing Apache Kafka for physical multi-agent scaling.

---

## 🏆 Key Research Findings

Evaluated over 35 independent trials per topology on rigorous reasoning, logic, and constraint-satisfaction benchmarks:

| Topology | Runs | Accuracy (%) | 95% Confidence Interval | Mean Tokens | Mean Cost | Mean Latency | Betweenness ($\mathcal{C}_B$) | Density ($D$) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tree (Hierarchical)** | 35 | **31.43%** | [16.05%, 46.81%] | 14,456 | $0.0024 | 116.9s | 0.095 | 0.057 |
| **Emergent (Dynamic)** | 35 | **28.57%** | [13.60%, 43.54%] | 19,945 | $0.0043 | 118.0s | 0.060 | 0.062 |
| **Star (Hub & Spoke)** | 35 | **22.86%** | [8.95%, 36.77%] | 16,623 | $0.0023 | 115.3s | 0.086 | 0.034 |
| **Mesh (All-to-All)** | 35 | **20.00%** | [6.75%, 33.25%] | 12,687 | $0.0032 | 119.9s | 0.071 | 0.086 |
| **Chain (Sequential)** | 35 | **17.14%** | [4.66%, 29.63%] | 12,679 | $0.0033 | 118.1s | 0.071 | 0.036 |

### Core Insights:
1. **The Tree Topology Advantage**: Hierarchical sub-problem decomposition achieves the highest accuracy while insulating deliberation sub-trees from context pollution.
2. **The Mesh Density Paradox**: Maximum graph density ($D = 0.086$) and unconstrained lateral chatter does *not* improve reasoning; Mesh underperforms Tree by 11.43 percentage points.
3. **Multi-Hop Attenuation**: Sequential pipelines (Chain) suffer rapid semantic drift across handoffs, yielding the lowest accuracy (17.14%).
4. **SNA Inverse Communication Law**: Total message count strongly negatively correlates with task success ($r = -0.602, p < 0.0001$). Successful teams communicate concisely; failing teams loop in repetitive verification cycles.

---

## 🏗️ Repository Architecture

The repository is organized modularly for strict separation of concerns, reproducibility, and deployment:

```
AgentMesh/
├── backend/                       # FastAPI research engine & distributed agent services
│   ├── app/
│   │   ├── models/                # SQLAlchemy database models (experiments, turns, metrics)
│   │   ├── routes/                # REST endpoints (experiments, topologies, analysis)
│   │   ├── schemas/               # Pydantic schemas and serialization models
│   │   ├── services/              # LLM client orchestration, evaluation, SNA metrics
│   │   └── topologies/            # Algorithmic topology engines (Star, Chain, Tree, Mesh, Stream)
│   ├── specialist_runner.py       # Standalone Kafka worker: Domain Specialist agent
│   ├── supervisor_runner.py       # Standalone Kafka worker: Supervisor / Router agent
│   ├── validator_runner.py        # Standalone Kafka worker: Solution Validator agent
│   ├── task_injector.py           # Benchmark task injector for Kafka topics
│   ├── .env.demo.example          # Environment variable template for demo deployments
│   ├── Dockerfile                 # Multi-stage Python 3.11 production container
│   └── requirements.txt           # Backend dependencies
│
├── frontend/                      # React 18 + Vite research inspection dashboard
│   ├── src/                       # Graph visualizers, topology comparators, failure inspectors
│   ├── Dockerfile                 # Multi-stage Node builder → Alpine Nginx server
│   └── nginx.conf                 # Production reverse proxy and SPA router
│
├── paper/                         # Publication LaTeX manuscript and build scripts
│   ├── main.tex                   # Complete academic paper (ACL/ACM format, embedded bib)
│   ├── README.md                  # Compilation guide and paper overview
│   ├── compile.bat                # 1-click Windows LaTeX compiler
│   └── compile.sh                 # 1-click Unix/macOS LaTeX compiler
│
├── results/                       # Empirical benchmark dataset and analysis suite
│   ├── figures/                   # 6 publication-ready figures (300 DPI)
│   ├── experiment_results.csv     # All 175 runs with 27 measured metrics
│   ├── statistical_summary.json   # Aggregated metrics, 95% CIs, and correlation matrices
│   ├── paper_results_section.md   # Publication tables and Markdown drafts
│   ├── traces.jsonl               # Comprehensive raw LLM execution traces (2.1 MB)
│   ├── transcripts/               # 175 complete markdown deliberation transcripts
│   └── README.md                  # Detailed data dictionary and replication instructions
│
├── benchmark/                     # Benchmark harness and distributed demonstration scripts
├── datasets/                      # Benchmark task definitions (Knights & Knaves, logic, coding)
├── analysis/                      # Statistical calculation and figure generator scripts
│
├── demo.bat                       # 1-click Windows launcher (interactive menu, Docker & Multi-term)
├── demo.sh                        # 1-click Unix launcher (interactive menu, Docker & Multi-term)
├── docker-compose.demo.yml        # Full 11-container distributed Kafka + multi-Ollama stack
├── task_injector.py               # Root CLI task injector wrapper
└── README.md                      # This conference submission documentation
```

---

## 🚀 Quickstart & Demonstration Options

AgentMesh supports three distinct demonstration modes depending on available infrastructure:

### 🎬 Option 1: Zero-Infrastructure In-Memory Stream (30 seconds)
Requires only Python with no external message broker:
```bash
cd backend
python -c "
import sys; sys.path.insert(0, '.')
from app.topologies.stream import run_message_stream_pipeline
result = run_message_stream_pipeline(
    'demo_001',
    'A says B is a knave. B says A and I are of different types. Who is who?'
)
print('Status:', result['status'])
print('Final Answer:', result['final_answer'][:250])
"
```

---

### 🐳 Option 2: Dockerized Full-Stack Distributed Cluster (Recommended)
Spawns **Apache Kafka (KRaft)**, **Kafka UI**, **3 isolated Ollama LLM nodes**, **4 autonomous agent runners**, the **FastAPI backend**, and the **React Dashboard**:

#### Windows:
```cmd
demo.bat 2
```

#### Linux / macOS:
```bash
chmod +x demo.sh
./demo.sh 2
```

#### Or directly via Docker Compose:
```bash
docker compose -f docker-compose.demo.yml up -d
```

**Live Web Interfaces:**
- 📊 **Research Dashboard**: [http://localhost](http://localhost)
- 🔌 **FastAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 📨 **Kafka UI Broker Console**: [http://localhost:8090](http://localhost:8090)
- 🤖 **Ollama Node A (Supervisor)**: [http://localhost:11434](http://localhost:11434)
- 🤖 **Ollama Node B (Specialist)**: [http://localhost:11435](http://localhost:11435)
- 🤖 **Ollama Node C (Validator)**: [http://localhost:11436](http://localhost:11436)

**Injecting Benchmark Tasks into Kafka:**
```bash
# Windows
demo.bat inject

# Linux / macOS
./demo.sh inject
```

---

### 🖥️ Option 3: Multi-Terminal Architecture Demonstration
Launches **4 color-coded terminal windows** demonstrating live, concurrent asynchronous message passing across topics:
- 🔵 **Cyan Terminal**: Supervisor Agent (consumes `tasks` $\to$ publishes `routing-decisions`)
- 🟡 **Yellow Terminal**: Specialist Coding Agent (consumes `routing-decisions` $\to$ publishes `specialist-results`)
- 🟠 **Orange Terminal**: Specialist Reasoning Agent (consumes `routing-decisions` $\to$ publishes `specialist-results`)
- 🟣 **Magenta Terminal**: Validator Agent (consumes `specialist-results` $\to$ publishes `validations`)

```bash
# Windows
demo.bat 3

# Linux / macOS
./demo.sh 3
```

---

## 📈 Empirical Results & Publication Figures

| Figure | Metric | Visualization |
|:---:|:---:|:---:|
| **Fig. 1** | Topology Accuracy | `results/figures/fig1_accuracy_by_topology_and_model.png` |
| **Fig. 2** | Failure Signatures Heatmap | `results/figures/fig2_failure_signatures_heatmap.png` |
| **Fig. 3** | Failure Distribution by Graph | `results/figures/fig3_failure_distribution_by_topology.png` |
| **Fig. 4** | SNA Pearson Correlation Matrix | `results/figures/fig4_sna_correlation_matrix.png` |
| **Fig. 5** | Model Robustness Interaction | `results/figures/fig5_model_robustness_interaction.png` |
| **Fig. 6** | Cost-Accuracy Pareto Frontier | `results/figures/fig6_cost_accuracy_pareto.png` |

---

## 📄 Compiling the LaTeX Paper

The camera-ready manuscript is located in [`paper/main.tex`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/paper/main.tex).

```bash
cd paper

# Windows
compile.bat

# Linux / macOS
chmod +x compile.sh
./compile.sh

# Or standard pdfLaTeX
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```
Output: `paper/main.pdf`

---

## 🔬 Reproducibility & Replication

To re-run the benchmark suite across prompt slices:
```bash
# Windows (Prompts 1 to 7)
run_experiments.bat 1 7

# Linux / macOS
chmod +x run_experiments.sh
./run_experiments.sh 1 7
```

To recompute statistical tables and generate all 6 figures from raw CSV data:
```bash
python analysis/analyze_results.py --input results/experiment_results.csv --output results/
```

---

## 📜 Citation

```bibtex
@inproceedings{agentmesh2026,
  title     = {AgentMesh: Communication Topology as a First-Class Architectural Variable in Multi-Agent LLM Systems},
  author    = {AgentMesh Research Team},
  booktitle = {Proceedings of the International Conference on Autonomous Agents and Multiagent Systems (AAMAS)},
  year      = {2026}
}
```

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
