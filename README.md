# MAST Topology Lab 🔬🌐
> **Multi-Agent System Topology Research Platform for LLMs**  
> Empirical investigation of communication graph topology, network metrics, and failure modes in collaborative multi-agent LLM reasoning.

---

## 1. Project Purpose

In multi-agent large language model (LLM) architectures, agents collaborate to solve complex reasoning, fact verification, and decision-making tasks. While prompting and agent roles are heavily researched, **how agents communicate—their network topology—exerts a structural influence on collective reasoning outcomes.**

**MAST Topology Lab** is an academic experimental platform designed to systematically evaluate:
1. **Communication Topologies**: How routing constraints in **Star**, **Chain**, and **Mesh** networks affect solution accuracy and message volume.
2. **Failure Categorization**: How topology correlates with specific failure modes (*Premature Agreement*, *Information Loss*, *Hallucination*, *Contradiction*, *Wrong Final Answer*).
3. **Network Analysis**: NetworkX graph centrality metrics (degree, betweenness centrality, communication density) mapped directly to agent performance.
4. **Statistical Significance**: Empirical validation using SciPy Chi-Square ($\chi^2$) tests of independence.

---

## 2. System Architecture

```
                                    +------------------------------------------+
                                    |         React + Vite Research UI         |
                                    | (Dashboard, Runner, Inspector, Compare)  |
                                    +--------------------+---------------------+
                                                         | REST / JSON
                                                         v
+--------------------------------------------------------------------------------------------------------+
|                                           FastAPI Backend                                              |
|                                                                                                        |
|  +---------------------+   +---------------------+   +---------------------+   +--------------------+  |
|  |   Topology Engine   |   |    Agent Service    |   |     LLM Service     |   | Evaluation Engine  |  |
|  |  (Star, Chain, Mesh)|   | (4-6 Defined Roles) |   | (OpenAI / Simulated)|   | (2-Stage Diagnosis)|  |
|  +----------+----------+   +----------+----------+   +----------+----------+   +---------+----------+  |
|             |                         |                         |                        |             |
|             +-------------------------+------------+------------+------------------------+             |
|                                                    |                                                   |
|                                                    v                                                   |
|                                   +---------------------------------+                                  |
|                                   |    Experiment Runner Service    |                                  |
|                                   |  - Enforces topology routing    |                                  |
|                                   |  - Logs turns to SQLite DB      |                                  |
|                                   |  - Computes NetworkX metrics    |                                  |
|                                   |  - Computes SciPy Chi-Square    |                                  |
|                                   +---------------------------------+                                  |
+----------------------------------------------------+---------------------------------------------------+
                                                     |
                                                     v
                                       +---------------------------+
                                       |  SQLite Database Storage  |
                                       |  (tasks, exp, messages)   |
                                       +---------------------------+
```

---

## 3. Core Features

- **Algorithmic Topology Engine**: Strictly enforces communication permissions for:
  - **STAR**: Single central coordinator hub with peripheral agents; no lateral communication.
  - **CHAIN**: Sequential deterministic pipeline ($A_1 \to A_2 \to \dots \to A_N$).
  - **MESH**: Fully interconnected all-to-all peer network.
- **Configurable Agent Teams (4 to 6 Roles)**:
  - `Coordinator`: Task decomposition, synthesis, final decision.
  - `Solver`: Analytical step-by-step logic.
  - `Critic`: Adversarial counterexamples and flaw detection.
  - `Fact Checker`: Boundary constraint & empirical fact verification.
  - `Alternative Solver`: Counter-hypothesis formulation (5+ agents).
  - `Final Reviewer`: Quality assurance & criteria validation (6 agents).
- **Two-Stage Failure Taxonomy**:
  - **Stage 1**: Solution correctness verification against criteria.
  - **Stage 2**: Evaluator diagnosis into the 5 core MAST categories:
    1. *Wrong Final Answer*
    2. *Hallucination / Unsupported Claim*
    3. *Contradiction*
    4. *Premature Agreement*
    5. *Information Loss*
- **NetworkX Graph Metrics**:
  - Degree & In/Out-degree per agent.
  - Normalized Betweenness Centrality.
  - Communication Network Density ($\rho$).
  - Interactive SVG visual graph with directional weights.
- **SciPy Statistical Analysis**:
  - Real-time contingency matrix generation ($3 \text{ topologies} \times 6 \text{ failure types}$).
  - Chi-Square test of independence ($\chi^2$, $p$-value, $df$, significance interpretation).
- **Hybrid LLM Engine**:
  - Configurable live API completions (OpenAI, Gemini, Ollama, Groq).
  - Built-in persona-consistent Simulation Engine for offline testing and rapid dataset generation.

---

## 4. Topologies Detailed

| Topology | Structure | Description & Characteristics |
| :--- | :--- | :--- |
| **STAR** | $A_1 \leftrightarrow A_i$ | **Hub-and-Spoke**: Agent 1 (Coordinator) delegates and gathers all feedback. High betweenness centrality on the hub; prone to *Premature Agreement* if coordinator locks onto early theories. |
| **CHAIN** | $A_1 \to A_2 \to \dots \to A_N$ | **Sequential Pipeline**: High latency, linear context handoff. Vulnerable to *Information Loss* across multi-hop transmission. |
| **MESH** | All-to-All | **Dense Network**: Maximum cross-critique and error recovery. Highest communication volume and density ($\rho \to 1.0$). |

---

## 5. Benchmark Task Categories

1. **Reasoning**: Multi-step deductive logic, constraint satisfaction, Knights & Knaves, river crossings, conference scheduling.
2. **Question Answering**: Multi-dimension factual synthesis, physics comparisons (JWST vs Hubble), distributed consensus architecture (Raft vs Paxos).
3. **Decision / Summary**: Incident triage under resource pressure (Black Friday database triage), Emergency Department clinical triage protocols.

---

## 6. Installation & Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment (Optional - default runs in Simulation Mode)
cp .env.example .env

# Start FastAPI server (Auto-creates SQLite tables & seeds tasks)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be live at: `http://127.0.0.1:8000` (API Docs at `http://127.0.0.1:8000/docs`).

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend will be live at: `http://localhost:5173`.

---

## 7. Environment Variables (`backend/.env`)

```ini
# Optional: Live LLM Provider (Leave empty to use built-in offline simulation)
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Runtime Mode
USE_MOCK_LLM=false
MAX_AGENT_TURNS=10
DATABASE_URL=sqlite:///./mast_lab.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
```

---

## 8. Running Automated Tests

Run the complete backend test suite:

```bash
# Run pytest with PYTHONPATH
python -m pytest backend/tests -v
```

All unit and integration tests verify:
- Star, Chain, and Mesh routing permissions.
- Message filtering and context visibility.
- NetworkX graph calculation (degree, betweenness, density).
- Failure classification logic.
- SciPy Chi-Square calculations and contingency matrices.
- FastAPI REST API endpoints.

---

## 9. Demonstration Walkthrough

1. **Open Dashboard** (`http://localhost:5173`):
   - Review overall KPI statistics, accuracy charts, and recent experimental runs.
2. **Launch a Trial** (Click **Run Experiment**):
   - Select `Knights and Knaves Island Logic` under **Reasoning**.
   - Select **STAR** topology, 4 agents, 6 turns.
   - Click **Run Single Experiment**. Watch live agent dialogue stream.
3. **Inspect Experiment**:
   - Examine the **Communication Topology Graph** (hover nodes to view Betweenness Centrality & Degrees).
   - Review the final answer vs expected answer and the Stage 2 failure taxonomy explanation.
   - Read the step-by-step chronological communication transcript.
4. **Compare Across Topologies**:
   - Run the same task on **CHAIN** and **MESH**, or click **Run 3-Topology Sweep** to execute repeated trials.
   - Navigate to **Compare Topologies** to inspect the Side-by-Side Matrix, the **Chi-Square ($\chi^2$) statistic & $p$-value**, and academic research takeaways.

---

## 10. Project Limitations & Future Work

- **Scope Boundary**: Focused on static Star, Chain, and Mesh graphs for 4–6 agents to guarantee clean academic rigor.
- **Future Directions**:
  - Dynamic/adaptive topology reconfiguration during runtime.
  - Multi-LLM heterogeneous teams (e.g. Claude + GPT-4 + Gemini).
  - Scaled benchmark suites (GSM8K, MATH, HumanEval).
  - Mixed-effects regression modeling on agent token costs.

---

## License
Academic Research MVP - Built for Multi-Agent System Topology Studies.
