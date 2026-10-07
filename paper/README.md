# AgentMesh Research Paper

This directory contains the LaTeX source and build assets for the research paper:

> **AgentMesh: Communication Topology as a First-Class Architectural Variable in Multi-Agent LLM Systems**  
> *Target Venue: International Conference on Autonomous Agents and Multiagent Systems (AAMAS) / Empirical Methods in Natural Language Processing (EMNLP)*

---

## 📑 Paper Overview

Modern multi-agent LLM systems routinely treat communication topology as an implicit implementation detail rather than an explicit architectural design choice. This paper establishes that **communication topology directly dictates multi-agent reasoning fidelity, error resilience, and communication overhead**.

### Core Contributions:
1. **The AgentMesh Benchmark Suite**: Custom-authored 70-prompt benchmark dataset specifically structured across the Multi-Agent System Taxonomy (MAST) covering Specification Adherence (FC1), Context & Coordination (FC2), and Convergence & Verification (FC3).
2. **Controlled Empirical Evaluation Across 5 Topologies**: 175 rigorous experimental trials evaluating Tree, Emergent, Star, Mesh, and Chain topologies with a fixed heterogeneous multi-LLM team.
3. **Social Network Analysis (SNA) Formalism**: Quantitative correlation between graph properties ($\mathcal{C}_B$, $D$, $\mathcal{R}$) and collective reasoning outcomes, discovering the Inverse Communication Law ($r = -0.602, p < 0.0001$).
4. **Quantified Failure Signature Taxonomy**: Extraction of six transcript-derived behavioural markers across all 14 MAST failure modes (FM-1.1 through FM-3.3).
5. **Architectural Design Principles**: Concrete engineering guidelines identifying when hierarchical branching, sequential pipelines, or dynamic routing should be deployed.

---

## 🖼️ Included Figures and Results

All figures referenced in `main.tex` are located in `figures/` (synchronized with `../figures/` and `../results/figures/`):

| Figure | Source File | Description |
|:---|:---|:---|
| **Figure 1** | `fig1_accuracy_by_topology_and_model.png` | Task Success Rate (%) across topologies (Tree: 31.43%, Emergent: 28.57%, Star: 22.86%, Mesh: 20.00%, Chain: 17.14%) |
| **Figure 2** | `fig2_failure_signatures_heatmap.png` | Quantified failure signature heatmap across 6 behavioral markers |
| **Figure 3** | `fig3_failure_distribution_by_topology.png` | Stacked distribution of failure modes by communication topology |
| **Figure 4** | `fig4_sna_correlation_matrix.png` | Pearson correlation matrix between graph metrics and reasoning outcomes ($r=-0.602$ messages vs. success, $r=+0.890$ betweenness vs. dominance) |
| **Figure 5** | `fig5_model_robustness_interaction.png` | Topological sensitivity envelope ($\mu \pm 1\sigma = 24.0\% \pm 5.92\%$) and task failure interaction profile |
| **Figure 6** | `fig6_cost_accuracy_pareto.png` | Communication overhead (tokens) vs. reasoning fidelity Pareto frontier |
| **Figure 7** | `fig7_topology_architectures.png` | Structural graph diagrams of the 5 communication network topologies |
| **Figure 8** | `fig8_evaluation_pipeline.png` | Two-Stage Evaluation and MAST Failure Diagnosis Pipeline flowchart |
| **Figure 9** | `fig9_latency_token_distributions.png` | Empirical distributions of token consumption and wall-clock latency |

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
