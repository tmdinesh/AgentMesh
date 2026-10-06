# AgentMesh Research Paper

This directory contains the LaTeX source and build assets for the research paper:

> **AgentMesh: Communication Topology as a First-Class Architectural Variable in Multi-Agent LLM Systems**  
> *Target Venue: International Conference on Autonomous Agents and Multiagent Systems (AAMAS) / Empirical Methods in Natural Language Processing (EMNLP)*

---

## 📑 Paper Overview

Modern multi-agent LLM systems routinely treat communication topology as an implicit implementation detail rather than an explicit architectural design choice. This paper establishes that **communication topology directly dictates multi-agent reasoning fidelity, error resilience, and communication overhead**.

### Core Contributions:
1. **Empirical Benchmarking Across 5 Topologies**: Systematic evaluation across **Tree**, **Emergent (Dynamic)**, **Star**, **Mesh**, and **Chain** topologies on complex reasoning and code generation tasks (175 total experimental runs).
2. **Social Network Analysis (SNA) Formalism**: Quantitative correlation between graph centrality metrics ($\mathcal{C}_B$, graph density $D$, reciprocity $\mathcal{R}$) and behavioural reasoning metrics (Dissent Ratio, Clarification Rate, Step Repetition Index, Coordinator Dominance).
3. **Failure Signature Taxonomy**: Quantification of multi-agent failure modes (**FM-1.1 Specification Non-Compliance**, **FM-1.3 Hallucination Cascade**, **FM-1.4 Information Attenuation**, **FM-1.5 Groupthink / Premature Agreement**).
4. **Kafka Event-Driven Stream Architecture**: Decoupled, partitioned asynchronous message streaming topology supporting horizontally scalable, multi-machine agent deployments.
5. **Reproducible Artifact Suite**: Full open-source benchmark suite, Dockerized distributed runner, raw deliberation traces, and automated Pareto frontier analysis.

---

## 🖼️ Included Figures and Results

All figures referenced in `main.tex` are located in `../results/figures/`:

| Figure | Source File | Description |
|:---|:---|:---|
| **Figure 1** | `fig1_accuracy_by_topology_and_model.png` | Task Success Rate (%) across topologies (Tree: 31.43%, Emergent: 28.57%, Star: 22.86%, Mesh: 20.00%, Chain: 17.14%) |
| **Figure 2** | `fig2_failure_signatures_heatmap.png` | Quantified failure signature heatmap across 6 behavioral markers |
| **Figure 3** | `fig3_failure_distribution_by_topology.png` | Stacked distribution of failure modes by communication topology |
| **Figure 4** | `fig4_sna_correlation_matrix.png` | Pearson correlation matrix between graph metrics and reasoning outcomes ($r=-0.602$ messages vs. success, $r=+0.890$ betweenness vs. dominance) |
| **Figure 5** | `fig5_model_robustness_interaction.png` | Topology robustness profiles showing topology accounts for ~41% of performance variance |
| **Figure 6** | `fig6_cost_accuracy_pareto.png` | Communication overhead (tokens) vs. reasoning fidelity Pareto frontier |

---

## 🛠️ How to Compile the Paper

### Method 1: Local TeX Distribution (TeX Live / MacTeX / MiKTeX)

The paper is formatted using standard LaTeX packages with an embedded `thebibliography` environment.

```bash
cd paper

# Linux / macOS
./compile.sh

# Windows (Command Prompt / PowerShell)
compile.bat

# Or manual compilation:
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

### Method 2: Docker TeX Live (No local LaTeX install needed)

```bash
docker run --rm -v "$(pwd)/..:/workspace" -w /workspace/paper \
  texlive/texlive:latest \
  pdflatex -interaction=nonstopmode main.tex
```

### Method 3: Overleaf / Cloud LaTeX
1. Zip the `paper/` directory and `results/figures/` directory.
2. Upload the zip to [Overleaf](https://www.overleaf.com).
3. Set compiler to **pdfLaTeX** and compile `main.tex`.

---

## 📂 Source Code & Data Mapping

- **LaTeX Source**: [`paper/main.tex`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/paper/main.tex)
- **Experimental Data**: [`results/experiment_results.csv`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/results/experiment_results.csv)
- **Statistical Summary**: [`results/statistical_summary.json`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/results/statistical_summary.json)
- **Full Trace Logs**: [`results/traces.jsonl`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/results/traces.jsonl)
- **Deliberation Transcripts**: [`results/transcripts/`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/results/transcripts/)
