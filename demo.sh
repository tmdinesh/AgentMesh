#!/usr/bin/env bash
# =============================================================================
# AgentMesh Kafka Demo Launcher (Linux / macOS)
# Usage:
#   ./demo.sh          → interactive menu
#   ./demo.sh 2        → Option 2: Docker full stack (single click)
#   ./demo.sh 3        → Option 3: Multi-terminal (tmux / background processes)
#   ./demo.sh inject   → inject 5 benchmark tasks
#   ./demo.sh stop     → stop everything
#   ./demo.sh logs     → stream Docker logs
#   ./demo.sh status   → health check
# =============================================================================

set -euo pipefail

BOLD="\033[1m"; DIM="\033[2m"
GREEN="\033[32m"; CYAN="\033[36m"; YELLOW="\033[33m"
RED="\033[31m"; MAGENTA="\033[35m"; BLUE="\033[34m"
ORANGE="\033[38;5;208m"; RESET="\033[0m"

COMPOSE_FILE="docker-compose.demo.yml"
LOG_DIR=".demo_logs"
PID_FILE=".demo_pids"

# =============================================================================
banner() {
  echo -e "${CYAN}${BOLD}"
  echo " ╔══════════════════════════════════════════════════════════════╗"
  echo " ║         AgentMesh — Multi-System Kafka Demo Launcher        ║"
  echo " ║  3 Ollama Models × Kafka Streams × Research Dashboard       ║"
  echo " ╚══════════════════════════════════════════════════════════════╝"
  echo -e "${RESET}"
}

# =============================================================================
menu() {
  echo -e " Which demo mode do you want?\n"
  echo -e " ${CYAN}${BOLD}[2]${RESET}  OPTION 2 — Docker Full Stack ${DIM}(recommended)${RESET}"
  echo -e "      Kafka + 3 Ollama + 4 Agents + Dashboard — all containerised"
  echo -e "      Requires: Docker\n"
  echo -e " ${YELLOW}${BOLD}[3]${RESET}  OPTION 3 — Multi-Terminal ${DIM}(shows live architecture)${RESET}"
  echo -e "      Starts 4 background agent processes + live log tailing"
  echo -e "      Requires: Python + Ollama installed locally\n"
  echo -e " ${DIM}[Q]  Quit${RESET}\n"
  read -rp "  Enter choice [2/3/Q]: " CHOICE

  case "$CHOICE" in
    2) option2 ;;
    3) option3 ;;
    [Qq]) echo "Bye!" && exit 0 ;;
    *) echo -e "${RED}Invalid choice.${RESET}" && menu ;;
  esac
}

# =============================================================================
check_docker() {
  command -v docker >/dev/null 2>&1 \
    || { echo -e "${RED}[ERROR] Docker not found. Install from https://docker.com${RESET}"; exit 1; }
  docker info >/dev/null 2>&1 \
    || { echo -e "${RED}[ERROR] Docker not running. Start Docker Desktop.${RESET}"; exit 1; }
  echo -e "${GREEN}[✓] Docker is running${RESET}"
}

check_python() {
  command -v python3 >/dev/null 2>&1 \
    || { echo -e "${RED}[ERROR] python3 not found.${RESET}"; exit 1; }
  echo -e "${GREEN}[✓] Python3 found: $(python3 --version)${RESET}"
}

check_ollama() {
  command -v ollama >/dev/null 2>&1 \
    || { echo -e "${YELLOW}[WARN] ollama not in PATH. Ensure it's running on http://localhost:11434${RESET}"; return 0; }
  ollama list 2>/dev/null | grep -qi "llama3" || {
    echo -e "${YELLOW}[SETUP] Pulling llama3:latest — this may take a few minutes...${RESET}"
    ollama pull llama3:latest
  }
  echo -e "${GREEN}[✓] Ollama model ready${RESET}"
}

ensure_env_demo() {
  if [ ! -f "backend/.env.demo" ]; then
    echo -e "${YELLOW}[SETUP] Creating backend/.env.demo...${RESET}"
    cat > backend/.env.demo << 'EOF'
AICREDITS_API_KEY=
USE_MOCK_LLM=false
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
USE_REAL_KAFKA=false
MAX_AGENT_TURNS=10
CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:5173
EOF
    echo -e "${YELLOW}[SETUP] Add AICREDITS_API_KEY to backend/.env.demo for cloud fallback.${RESET}"
  fi
}

wait_for_kafka() {
  echo -ne "\n${BOLD}Waiting for Kafka to be healthy${RESET}"
  local retries=25
  until docker compose -f "$COMPOSE_FILE" exec -T kafka \
        kafka-topics.sh --bootstrap-server localhost:9092 --list >/dev/null 2>&1; do
    retries=$((retries - 1))
    [ $retries -le 0 ] && { echo -e "\n${RED}[ERROR] Kafka did not start.${RESET}"; exit 1; }
    printf "."
    sleep 3
  done
  echo -e " ${GREEN}ready!${RESET}"
}

# =============================================================================
option2() {
  echo -e "\n${CYAN}${BOLD} ┌─────────────────────────────────────────────┐"
  echo -e " │  OPTION 2 — Docker Full Stack               │"
  echo -e " │  Kafka + 3 Ollama + Agents + Dashboard      │"
  echo -e " └─────────────────────────────────────────────┘${RESET}\n"

  check_docker
  ensure_env_demo

  echo -e "\n${BOLD}[1/5] Building AgentMesh images...${RESET}"
  docker compose -f "$COMPOSE_FILE" build --quiet

  echo -e "\n${BOLD}[2/5] Starting Kafka + Kafka UI + Ollama instances...${RESET}"
  docker compose -f "$COMPOSE_FILE" --profile cpu up -d kafka kafka-ui ollama-b ollama-c

  wait_for_kafka

  echo -e "\n${BOLD}[4/5] Pulling Ollama models (mistral:7b, phi3:medium)...${RESET}"
  docker compose -f "$COMPOSE_FILE" run --rm model-puller 2>/dev/null || true

  echo -e "\n${BOLD}[5/5] Starting all AgentMesh services...${RESET}"
  docker compose -f "$COMPOSE_FILE" --profile cpu up -d

  print_urls_docker

  echo -e "\n${BOLD}Auto-injecting 5 benchmark tasks in 15s...${RESET}"
  sleep 15
  inject_tasks
}

# =============================================================================
option3() {
  echo -e "\n${YELLOW}${BOLD} ┌──────────────────────────────────────────────────────────┐"
  echo -e " │  OPTION 3 — Multi-Terminal (shows architecture live)    │"
  echo -e " │  4 Agent Processes + Live Log Tailing                   │"
  echo -e " └──────────────────────────────────────────────────────────┘${RESET}\n"

  check_python
  check_ollama

  # Install deps
  echo -e "\n${BOLD}[SETUP] Installing backend dependencies...${RESET}"
  pip3 install -q -r backend/requirements.txt

  # Create log dir & clean old pids
  mkdir -p "$LOG_DIR"
  > "$PID_FILE"

  # Kill any leftover agents
  stop_option3_procs 2>/dev/null || true

  echo -e "\n${BOLD}[LAUNCH] Starting 4 agent processes in background...${RESET}\n"

  # ── Supervisor ─────────────────────────────────────────────────────────────
  AGENT_1_MODEL=llama3:latest \
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  USE_REAL_KAFKA=false \
  python3 backend/supervisor_runner.py \
    > "$LOG_DIR/supervisor.log" 2>&1 &
  echo $! >> "$PID_FILE"
  echo -e " ${CYAN}${BOLD}[1/4] Supervisor${RESET}       PID=$! — log: $LOG_DIR/supervisor.log"
  sleep 1

  # ── Specialist (coding) ────────────────────────────────────────────────────
  AGENT_2_MODEL=llama3:latest \
  SPECIALIST_TYPE=coding \
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  USE_REAL_KAFKA=false \
  python3 backend/specialist_runner.py \
    > "$LOG_DIR/specialist_coding.log" 2>&1 &
  echo $! >> "$PID_FILE"
  echo -e " ${YELLOW}${BOLD}[2/4] Specialist:coding${RESET}  PID=$! — log: $LOG_DIR/specialist_coding.log"
  sleep 1

  # ── Specialist (reasoning) ─────────────────────────────────────────────────
  AGENT_2_MODEL=llama3:latest \
  SPECIALIST_TYPE=reasoning \
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  USE_REAL_KAFKA=false \
  python3 backend/specialist_runner.py \
    > "$LOG_DIR/specialist_reasoning.log" 2>&1 &
  echo $! >> "$PID_FILE"
  echo -e " ${ORANGE}${BOLD}[3/4] Specialist:reasoning${RESET} PID=$! — log: $LOG_DIR/specialist_reasoning.log"
  sleep 1

  # ── Validator ──────────────────────────────────────────────────────────────
  AGENT_3_MODEL=llama3:latest \
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  USE_REAL_KAFKA=false \
  python3 backend/validator_runner.py \
    > "$LOG_DIR/validator.log" 2>&1 &
  echo $! >> "$PID_FILE"
  echo -e " ${MAGENTA}${BOLD}[4/4] Validator${RESET}         PID=$! — log: $LOG_DIR/validator.log"

  echo -e "\n${GREEN}${BOLD} ══════════════════════════════════════════════════════════"
  echo -e " ✅  4 Agent Processes Running!"
  echo ""
  echo -e " ${CYAN}Supervisor${RESET}         topics:  tasks → routing-decisions"
  echo -e " ${YELLOW}Specialist:coding${RESET}  topics:  routing-decisions → specialist-results"
  echo -e " ${ORANGE}Specialist:reason${RESET}  topics:  routing-decisions → specialist-results"
  echo -e " ${MAGENTA}Validator${RESET}          topics:  specialist-results → validations"
  echo -e "${GREEN} ══════════════════════════════════════════════════════════${RESET}\n"

  # ── Offer to tail logs or inject ──────────────────────────────────────────
  read -rp "  Inject 5 benchmark tasks now? [Y/n]: " INJ
  INJ="${INJ:-Y}"
  if [[ "$INJ" =~ ^[Yy] ]]; then
    echo -e "\n${BOLD}Waiting 5s for agents to initialise...${RESET}"
    sleep 5
    python3 task_injector.py
  fi

  echo -e "\n${BOLD}Tail all agent logs now? [Y/n]:${RESET}"
  read -rp "" TAIL_LOGS
  TAIL_LOGS="${TAIL_LOGS:-Y}"
  if [[ "$TAIL_LOGS" =~ ^[Yy] ]]; then
    tail_option3_logs
  else
    echo -e "\n${DIM}Logs: $LOG_DIR/{supervisor,specialist_coding,specialist_reasoning,validator}.log"
    echo -e "Stop: ./demo.sh stop${RESET}"
  fi
}

# =============================================================================
tail_option3_logs() {
  echo -e "\n${BOLD}Tailing all agent logs (Ctrl+C to stop tailing — agents keep running):${RESET}\n"

  # Use multitail if available, else staggered tail -f
  if command -v multitail >/dev/null 2>&1; then
    multitail \
      -cS bash "$LOG_DIR/supervisor.log" \
      -cS bash "$LOG_DIR/specialist_coding.log" \
      -cS bash "$LOG_DIR/specialist_reasoning.log" \
      -cS bash "$LOG_DIR/validator.log"
  else
    # Colour-coded tail simulation
    tail -f \
      "$LOG_DIR/supervisor.log" \
      "$LOG_DIR/specialist_coding.log" \
      "$LOG_DIR/specialist_reasoning.log" \
      "$LOG_DIR/validator.log" | \
    awk '
      /supervisor/     { print "\033[36m" $0 "\033[0m"; next }
      /specialist.*cod/ { print "\033[33m" $0 "\033[0m"; next }
      /specialist.*rea/ { print "\033[38;5;208m" $0 "\033[0m"; next }
      /validator/       { print "\033[35m" $0 "\033[0m"; next }
      { print }
    '
  fi
}

# =============================================================================
inject_tasks() {
  echo -e "\n${BOLD}[INJECT] Sending 5 benchmark tasks...${RESET}"

  # Try Docker first, fall back to direct Python
  if docker compose -f "$COMPOSE_FILE" ps backend 2>/dev/null | grep -q "running"; then
    echo -e "${DIM}(Mode: Docker / Option 2)${RESET}"
    sleep 5
    docker compose -f "$COMPOSE_FILE" exec backend python task_injector.py
  else
    echo -e "${DIM}(Mode: Direct Python / Option 3)${RESET}"
    python3 task_injector.py
  fi
}

# =============================================================================
stop_option3_procs() {
  if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
      kill "$pid" 2>/dev/null && echo -e "${DIM}Killed PID $pid${RESET}" || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
}

stop_all() {
  echo -e "\n${YELLOW}[STOP] Shutting down all AgentMesh processes...${RESET}"

  # Stop Docker stack
  docker compose -f "$COMPOSE_FILE" --profile cpu --profile gpu down 2>/dev/null \
    && echo -e "${GREEN}[✓] Docker stack stopped${RESET}" || true

  # Stop Option 3 background processes
  stop_option3_procs
  echo -e "${GREEN}[✓] Background agent processes stopped${RESET}"

  echo -e "${GREEN}[STOP] All done. Volumes and logs preserved.${RESET}"
}

show_logs() {
  echo -e "\n${BOLD}Streaming Docker logs (Ctrl+C to exit)...${RESET}"
  docker compose -f "$COMPOSE_FILE" logs -f --tail=50
}

show_status() {
  echo -e "\n${BOLD}── Docker Services ─────────────────────────────────────────${RESET}"
  docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || echo "(no Docker demo running)"

  echo -e "\n${BOLD}── Option 3 Agent Processes ────────────────────────────────${RESET}"
  if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
      if kill -0 "$pid" 2>/dev/null; then
        echo -e "  PID $pid — ${GREEN}running${RESET}"
      else
        echo -e "  PID $pid — ${RED}dead${RESET}"
      fi
    done < "$PID_FILE"
  else
    echo "  (no Option 3 agents started)"
  fi

  echo -e "\n${BOLD}── Kafka Topics (Docker) ───────────────────────────────────${RESET}"
  docker compose -f "$COMPOSE_FILE" exec -T kafka kafka-topics.sh \
    --bootstrap-server localhost:9092 --list 2>/dev/null || echo "  (Kafka not running)"

  echo -e "\n${BOLD}── Ollama Models (Local) ────────────────────────────────────${RESET}"
  ollama list 2>/dev/null || echo "  (Ollama not running)"
}

print_urls_docker() {
  echo -e ""
  echo -e "${GREEN}${BOLD} ══════════════════════════════════════════════════════════"
  echo -e " ✅  AgentMesh Docker Demo is UP!"
  echo ""
  echo -e " 📊  Research Dashboard   →  ${CYAN}http://localhost${GREEN}"
  echo -e " 🔌  FastAPI Docs         →  ${CYAN}http://localhost:8000/docs${GREEN}"
  echo -e " 📨  Kafka UI             →  ${CYAN}http://localhost:8090${GREEN}"
  echo -e " 🤖  Ollama (Supervisor)  →  ${CYAN}http://localhost:11434${GREEN}"
  echo -e " 🤖  Ollama (Specialist)  →  ${CYAN}http://localhost:11435${GREEN}"
  echo -e " 🤖  Ollama (Validator)   →  ${CYAN}http://localhost:11436${GREEN}"
  echo -e " ══════════════════════════════════════════════════════════${RESET}"
  echo ""
  echo -e "  ${BOLD}Commands:${RESET}"
  echo -e "  ./demo.sh inject  — inject 5 more tasks"
  echo -e "  ./demo.sh logs    — stream container logs"
  echo -e "  ./demo.sh status  — health check"
  echo -e "  ./demo.sh stop    — stop everything"
  echo ""
}

# =============================================================================
# Entry point
# =============================================================================
banner

CMD="${1:-}"
case "$CMD" in
  "")       menu ;;
  2)        option2 ;;
  3)        option3 ;;
  inject)   inject_tasks ;;
  stop)     stop_all ;;
  logs)     show_logs ;;
  status)   show_status ;;
  *)
    echo -e "${RED}Unknown command: $CMD${RESET}"
    echo "Usage: ./demo.sh [2|3|inject|stop|logs|status]"
    exit 1
    ;;
esac
