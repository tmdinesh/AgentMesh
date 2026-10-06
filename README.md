# AgentMesh 🌐🤖
> **Distributed Multi-Agent LLM Orchestration Platform**  
> A high-performance, modular system for building, visualizing, and running distributed multi-agent LLM systems with configurable communication topologies and Apache Kafka event streaming.

---

## 🌟 Overview

**AgentMesh** is an open-source distributed platform for multi-agent LLM systems. It enables multiple autonomous LLM agents to collaborate on complex tasks through structured communication patterns, real-time message routing, and event-driven distributed streaming.

Whether running locally on a single machine or across a distributed cluster of microservices, AgentMesh decouples agent roles, coordinates interactions, and provides a rich web dashboard for real-time monitoring and inspection.

---

## 🏗️ Architecture

```
                               +------------------------------------------+
                               |         React 18 + Vite Web App          |
                               | (Dashboard, Live Inspector, Diagnostics) |
                               +--------------------+---------------------+
                                                    | HTTP / REST
                                                    v
+--------------------------------------------------------------------------------------------------------+
|                                           FastAPI Backend                                              |
|                                                                                                        |
|  +---------------------+   +---------------------+   +---------------------+   +--------------------+  |
|  |   Topology Engine   |   |    Agent Service    |   |     LLM Service     |   | Diagnostics Engine |  |
|  | (Tree, Star, Mesh)  |   | (Supervisor/Workers)|   | (Ollama / Cloud LLM)|   | (Message Tracking) |  |
|  +----------+----------+   +----------+----------+   +----------+----------+   +---------+----------+  |
|             |                         |                         |                        |             |
|             +-------------------------+------------+------------+------------------------+             |
|                                                    |                                                   |
|                                                    v                                                   |
|                                   +---------------------------------+                                  |
|                                   |  Apache Kafka Event Stream Bus  |                                  |
|                                   |  (tasks -> routing -> results)  |                                  |
|                                   +---------------------------------+                                  |
+----------------------------------------------------+---------------------------------------------------+
                                                     |
                                                     v
                                       +---------------------------+
                                       |      SQLite / Storage     |
                                       |  (runs, turns, messages)  |
                                       +---------------------------+
```

### Core Components:
1. **FastAPI Backend (`backend/`)**: High-throughput REST API serving orchestration workflows, agent registration, network analysis, and task routing.
2. **React Dashboard (`frontend/`)**: Modern web UI for inspecting live agent interactions, network graphs, token consumption, and diagnostics.
3. **Kafka Event Stream Topology (`backend/app/topologies/stream.py`)**: Distributed pub-sub pipeline supporting horizontally scalable, decoupled agent workers.
4. **Standalone Agent Microservices (`backend/*_runner.py`)**: Dedicated workers for Supervisor, Specialists (Coding, Reasoning), and Solution Validators.
5. **Actor & Topology Engine (`topologies/actor_system.py`)**: Algorithmic communication graph controllers enforcing Star, Chain, Tree, Mesh, and Dynamic routing constraints.

---

## 🚀 Quickstart

### Option A: 1-Click Docker Full-Stack Deployment (Recommended)

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

#### Direct Docker Compose:
```bash
docker compose -f docker-compose.demo.yml up -d
```

#### Access Web Interfaces:
- 📊 **Web Dashboard**: [http://localhost](http://localhost)
- 🔌 **FastAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 📨 **Kafka UI Broker Console**: [http://localhost:8090](http://localhost:8090)
- 🤖 **Ollama Node A (Supervisor)**: [http://localhost:11434](http://localhost:11434)
- 🤖 **Ollama Node B (Specialist)**: [http://localhost:11435](http://localhost:11435)
- 🤖 **Ollama Node C (Validator)**: [http://localhost:11436](http://localhost:11436)

#### Inject Tasks into the Live Pipeline:
```bash
# Windows
demo.bat inject

# Linux / macOS
./demo.sh inject
```

---

### Option B: Multi-Terminal Distributed Demo

Spawns separate terminal windows showing live inter-agent message passing across Kafka topics in real time:

- 🔵 **Supervisor Window**: Consumes `tasks` → publishes `routing-decisions`
- 🟡 **Specialist (Coding)**: Consumes `routing-decisions` → publishes `specialist-results`
- 🟠 **Specialist (Reasoning)**: Consumes `routing-decisions` → publishes `specialist-results`
- 🟣 **Validator**: Consumes `specialist-results` → publishes `validations`

```bash
# Windows
demo.bat 3

# Linux / macOS
./demo.sh 3
```

---

### Option C: Local Development Setup

#### 1. Backend Setup:
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```

Dashboard is available at `http://localhost:5173`.

---

## 🛠️ Configuration

Environment variables can be customized in [`backend/.env.demo`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/backend/.env.demo) or [`backend/.env.demo.example`](file:///c:/Users/Dinesh.LAPTOP-OO5HEB93/Downloads/AgentMesh/backend/.env.demo.example):

| Variable | Default | Description |
|:---|:---|:---|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker endpoints |
| `USE_REAL_KAFKA` | `false` | `false` for embedded broker; `true` for live cluster |
| `DATABASE_URL` | `sqlite:////data/mast_lab.db` | Application database connection string |
| `MAX_AGENT_TURNS` | `10` | Maximum deliberation cycles per task |
| `AICREDITS_API_KEY` | — | Optional cloud LLM API key |
| `USE_MOCK_LLM` | `false` | Enable deterministic mock responses for testing |

---

## 📂 Modular Repository Layout

```
AgentMesh/
├── backend/                       # FastAPI backend & standalone Kafka agent runners
│   ├── app/                       # Application routers, models, schemas, services
│   ├── specialist_runner.py       # Domain specialist agent service
│   ├── supervisor_runner.py       # Supervisor router agent service
│   ├── validator_runner.py        # Validator agent service
│   ├── task_injector.py           # Task injection utility
│   ├── Dockerfile                 # Backend container definition
│   └── requirements.txt           # Python dependencies
│
├── frontend/                      # React 18 + Vite web dashboard
│   ├── src/                       # Components, state management, views
│   ├── Dockerfile                 # Production multi-stage Nginx container
│   └── nginx.conf                 # SPA router & reverse proxy
│
├── topologies/                    # Actor-based topology and communication abstractions
├── docs/                          # Architecture workflows and guides
│
├── demo.bat                       # Windows one-click interactive launcher
├── demo.sh                        # Linux/macOS one-click interactive launcher
├── docker-compose.demo.yml        # Full distributed 11-container Docker Compose
├── docker-compose.yml             # Lightweight local development stack
├── task_injector.py               # Root task injector CLI wrapper
└── README.md                      # Application documentation
```

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
