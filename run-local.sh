#!/usr/bin/env bash
# ==============================================================================
# MAST Topology Lab - Single-Click Local Launcher
# Launches FastAPI backend on port 8000 & React/Vite frontend on port 5173
# ==============================================================================

set -e

# Styling & Colors
BOLD='\033[1;37m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Cleanup function to kill child processes on exit
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${YELLOW}[!] Shutting down MAST Topology Lab services...${NC}"
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${CYAN}[-] Terminating Backend (PID: $BACKEND_PID)...${NC}"
    kill -TERM "$BACKEND_PID" 2>/dev/null || kill -9 "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${CYAN}[-] Terminating Frontend (PID: $FRONTEND_PID)...${NC}"
    kill -TERM "$FRONTEND_PID" 2>/dev/null || kill -9 "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo -e "${GREEN}[✓] All processes stopped cleanly. Goodbye!${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${BOLD}"
echo "=========================================================================="
echo "  🔬 MAST Topology Lab - Single-Click Launcher"
echo "=========================================================================="
echo -e "${NC}"

# 1. Pre-flight checks
echo -e "${CYAN}[1/5] Checking prerequisites...${NC}"

# Detect Python
if command -v python3 &>/dev/null; then
  PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
  PYTHON_BIN="python"
else
  echo -e "${RED}[ERROR] Python 3 is not installed or not in system PATH.${NC}"
  echo -e "${YELLOW}Please install Python 3.10+ and retry.${NC}"
  exit 1
fi

PY_VERSION=$($PYTHON_BIN --version 2>&1)
echo -e "${GREEN}  ✓ Found Python: ${PY_VERSION}${NC}"

# Detect Node & npm
if ! command -v node &>/dev/null; then
  echo -e "${RED}[ERROR] Node.js is not installed or not in system PATH.${NC}"
  echo -e "${YELLOW}Please install Node.js 18+ and retry.${NC}"
  exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}  ✓ Found Node.js: ${NODE_VERSION}${NC}"

if ! command -v npm &>/dev/null; then
  echo -e "${RED}[ERROR] npm is not installed or not in system PATH.${NC}"
  exit 1
fi

# 2. Virtual Environment Setup
echo -e "${CYAN}[2/5] Setting up Python virtual environment...${NC}"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo -e "${YELLOW}  Creating Python virtual environment in .venv ...${NC}"
  $PYTHON_BIN -m venv "$VENV_DIR"
fi

# Activate virtualenv
if [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
  source "$VENV_DIR/Scripts/activate"
fi

echo -e "${CYAN}  Installing/Verifying Python dependencies...${NC}"
python -m pip install -q --upgrade pip
python -m pip install -q -r backend/requirements.txt
echo -e "${GREEN}  ✓ Python environment ready.${NC}"

# 3. Environment Config Check
echo -e "${CYAN}[3/5] Checking backend configuration...${NC}"
if [ ! -f "backend/.env" ]; then
  echo -e "${YELLOW}  backend/.env not found. Creating default from backend/.env.example ...${NC}"
  cp backend/.env.example backend/.env
fi
echo -e "${GREEN}  ✓ Environment configuration verified.${NC}"

# 4. Frontend Package Setup
echo -e "${CYAN}[4/5] Checking frontend dependencies...${NC}"
if [ ! -d "frontend/node_modules" ]; then
  echo -e "${YELLOW}  frontend/node_modules not found. Running npm install...${NC}"
  (cd frontend && npm install)
fi
echo -e "${GREEN}  ✓ Frontend dependencies ready.${NC}"

# 5. Launch Services
echo -e "${CYAN}[5/5] Launching backend & frontend services...${NC}"

# Launch Backend
(cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

# Launch Frontend
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# Brief pause to verify startup
sleep 2

echo -e "${BOLD}"
echo "=========================================================================="
echo "  🚀 MAST Topology Lab is live!"
echo "=========================================================================="
echo -e "${NC}"
echo -e "  🌐 Frontend Dashboard: ${CYAN}http://localhost:5173${NC}"
echo -e "  ⚙️  Backend REST API:  ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  📖 Swagger API Docs:  ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Press [Ctrl+C] to gracefully stop all services.${NC}"
echo -e "=========================================================================="
echo ""

# Attempt to open browser automatically
if command -v open &>/dev/null; then
  open "http://localhost:5173" 2>/dev/null || true
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:5173" 2>/dev/null || true
elif command -v cmd.exe &>/dev/null; then
  cmd.exe /c start "http://localhost:5173" 2>/dev/null || true
fi

# Keep script running and wait for background processes
wait "$BACKEND_PID" "$FRONTEND_PID"
