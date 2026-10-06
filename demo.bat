@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: AgentMesh Kafka Demo Launcher (Windows)
:: Usage:
::   demo.bat          → interactive menu
::   demo.bat 2        → Option 2: Docker full stack (single click)
::   demo.bat 3        → Option 3: Multi-terminal (4 windows + injector)
::   demo.bat inject   → inject tasks into running demo
::   demo.bat stop     → stop all (Docker + Option 3 processes)
::   demo.bat logs     → stream Docker logs
::   demo.bat status   → check health
:: =============================================================================

title AgentMesh Kafka Demo
color 0A

call :banner

:: ── Route by first argument ───────────────────────────────────────────────────
set ARG=%~1
if "%ARG%"=="2"       goto option2
if "%ARG%"=="3"       goto option3
if "%ARG%"=="inject"  goto inject_tasks
if "%ARG%"=="stop"    goto stop_all
if "%ARG%"=="logs"    goto show_logs
if "%ARG%"=="status"  goto show_status
if "%ARG%"==""        goto menu

echo [ERROR] Unknown command: %ARG%
echo Usage: demo.bat [2^|3^|inject^|stop^|logs^|status]
exit /b 1

:: =============================================================================
:menu
:: =============================================================================
echo  Which demo mode do you want?
echo.
echo  [2]  OPTION 2 — Docker Full Stack (recommended)
echo         Kafka + 3 Ollama + 4 Agents + Dashboard — all in Docker
echo         Requires: Docker Desktop running
echo.
echo  [3]  OPTION 3 — Multi-Terminal (shows architecture live)
echo         Opens 4 separate windows: Supervisor, Specialist, Validator, Injector
echo         Requires: Python + Ollama installed locally
echo.
echo  [Q]  Quit
echo.
set /p CHOICE="  Enter choice [2/3/Q]: "

if /i "%CHOICE%"=="2" goto option2
if /i "%CHOICE%"=="3" goto option3
if /i "%CHOICE%"=="Q" goto end
echo Invalid choice. Try again.
goto menu


:: =============================================================================
:option2
:: =============================================================================
echo.
echo  ┌─────────────────────────────────────────────┐
echo  │  OPTION 2 — Docker Full Stack               │
echo  │  Kafka + 3 Ollama + Agents + Dashboard      │
echo  └─────────────────────────────────────────────┘
echo.

:: Check Docker
where docker >nul 2>&1 || (
    echo [ERROR] Docker not found. Install Docker Desktop: https://docker.com
    pause & exit /b 1
)
docker info >nul 2>&1 || (
    echo [ERROR] Docker daemon not running. Open Docker Desktop first.
    pause & exit /b 1
)
echo [OK] Docker is running.

:: Create .env.demo if missing
call :ensure_env_demo

echo.
echo [1/5] Building AgentMesh images...
docker compose -f docker-compose.demo.yml build --quiet
if !errorlevel! neq 0 (echo [ERROR] Build failed. & pause & exit /b 1)

echo.
echo [2/5] Starting Kafka + Kafka UI + Ollama instances...
docker compose -f docker-compose.demo.yml --profile cpu up -d kafka kafka-ui ollama-b ollama-c

echo.
echo [3/5] Waiting for Kafka to become healthy (up to 40s)...
set /a WAIT=0
:kafka_wait
timeout /t 3 /nobreak >nul
set /a WAIT+=3
docker compose -f docker-compose.demo.yml exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --list >nul 2>&1
if !errorlevel! equ 0 goto kafka_ready
if !WAIT! geq 40 (echo [ERROR] Kafka did not start in time. & pause & exit /b 1)
<nul set /p "=."
goto kafka_wait
:kafka_ready
echo  ready!

echo.
echo [4/5] Pulling Ollama models into containers (mistral:7b, phi3:medium)...
docker compose -f docker-compose.demo.yml run --rm model-puller >nul 2>&1
echo      Note: llama3:8b pulls automatically when supervisor starts.

echo.
echo [5/5] Starting all AgentMesh services...
docker compose -f docker-compose.demo.yml --profile cpu up -d

echo.
call :print_urls_docker

echo.
echo  Auto-injecting 5 benchmark tasks in 15 seconds...
timeout /t 15 /nobreak >nul
docker compose -f docker-compose.demo.yml exec backend python task_injector.py
goto end


:: =============================================================================
:option3
:: =============================================================================
echo.
echo  ┌─────────────────────────────────────────────────────────────┐
echo  │  OPTION 3 — Multi-Terminal (shows live architecture)        │
echo  │  Opens 4 windows: Supervisor │ Specialist │ Validator │ ...│
echo  └─────────────────────────────────────────────────────────────┘
echo.

:: Check Python
where python >nul 2>&1 || (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

:: Check Ollama
where ollama >nul 2>&1 || (
    echo [WARN] Ollama binary not found in PATH.
    echo        Download from https://ollama.com — or run anyway if Ollama is running.
    timeout /t 3 /nobreak >nul
)

:: Check model pulled
echo [CHECK] Verifying llama3:latest is available...
ollama list 2>nul | findstr /i "llama3" >nul 2>&1
if !errorlevel! neq 0 (
    echo [SETUP] Pulling llama3:latest — this may take a few minutes...
    ollama pull llama3:latest
)
echo [OK] Model ready.

:: Install backend dependencies
echo.
echo [SETUP] Installing backend Python dependencies...
cd backend
pip install -q -r requirements.txt
cd ..

:: Kill any leftover Option 3 processes
taskkill /f /fi "WINDOWTITLE eq AgentMesh*" >nul 2>&1

echo.
echo [LAUNCH] Opening agent terminal windows...

:: Window 1 — Supervisor
start "AgentMesh | Supervisor (llama3:latest)" cmd /k ^
  "color 0B && title AgentMesh ^| Supervisor (llama3:latest) && echo [SUPERVISOR] Consuming topic: tasks ^^> routing-decisions && echo. && cd backend && set AGENT_1_MODEL=llama3:latest && set KAFKA_BOOTSTRAP_SERVERS=localhost:9092 && set USE_REAL_KAFKA=false && python supervisor_runner.py"

timeout /t 2 /nobreak >nul

:: Window 2 — Specialist (coding)
start "AgentMesh | Specialist-Coding (llama3:latest)" cmd /k ^
  "color 0E && title AgentMesh ^| Specialist-Coding (llama3:latest) && echo [SPECIALIST] Consuming topic: routing-decisions ^^> specialist-results && echo. && cd backend && set AGENT_2_MODEL=llama3:latest && set SPECIALIST_TYPE=coding && set KAFKA_BOOTSTRAP_SERVERS=localhost:9092 && set USE_REAL_KAFKA=false && python specialist_runner.py"

timeout /t 2 /nobreak >nul

:: Window 3 — Specialist (reasoning)
start "AgentMesh | Specialist-Reasoning (llama3:latest)" cmd /k ^
  "color 06 && title AgentMesh ^| Specialist-Reasoning (llama3:latest) && echo [SPECIALIST] Consuming topic: routing-decisions ^^> specialist-results && echo. && cd backend && set AGENT_2_MODEL=llama3:latest && set SPECIALIST_TYPE=reasoning && set KAFKA_BOOTSTRAP_SERVERS=localhost:9092 && set USE_REAL_KAFKA=false && python specialist_runner.py"

timeout /t 2 /nobreak >nul

:: Window 4 — Validator
start "AgentMesh | Validator (llama3:latest)" cmd /k ^
  "color 0D && title AgentMesh ^| Validator (llama3:latest) && echo [VALIDATOR] Consuming topic: specialist-results ^^> validations && echo. && cd backend && set AGENT_3_MODEL=llama3:latest && set KAFKA_BOOTSTRAP_SERVERS=localhost:9092 && set USE_REAL_KAFKA=false && python validator_runner.py"

echo.
echo  ══════════════════════════════════════════════════════════
echo  ✅  4 Agent Windows Launched!
echo.
echo  Color Legend:
echo    [CYAN]    Supervisor       — routes tasks to specialists
echo    [YELLOW]  Specialist Code  — solves coding problems
echo    [ORANGE]  Specialist Reason— solves logic problems
echo    [MAGENTA] Validator        — validates and scores answers
echo  ══════════════════════════════════════════════════════════
echo.
echo  Inject tasks now? (waits 5s for agents to start)
set /p INJ="  [Y/N]: "
if /i "%INJ%"=="Y" (
    timeout /t 5 /nobreak >nul
    echo.
    echo [INJECT] Sending 5 benchmark tasks...
    start "AgentMesh | Task Injector" cmd /k ^
      "color 0F && title AgentMesh ^| Task Injector && echo Injecting tasks... && python task_injector.py && echo. && echo Done! Press any key to close. && pause"
)
goto end


:: =============================================================================
:inject_tasks
:: =============================================================================
echo.
echo [INJECT] Sending benchmark tasks...

:: Try Docker first, fall back to direct Python
docker compose -f docker-compose.demo.yml ps backend 2>nul | findstr "running" >nul 2>&1
if !errorlevel! equ 0 (
    echo [MODE] Injecting via Docker (Option 2)...
    timeout /t 5 /nobreak >nul
    docker compose -f docker-compose.demo.yml exec backend python task_injector.py
) else (
    echo [MODE] Injecting via Python directly (Option 3)...
    python task_injector.py
)
goto end


:: =============================================================================
:stop_all
:: =============================================================================
echo.
echo [STOP] Shutting down all AgentMesh processes...

:: Stop Docker stack
docker compose -f docker-compose.demo.yml --profile cpu --profile gpu down 2>nul
echo [STOP] Docker stack stopped.

:: Kill Option 3 windows by title
taskkill /f /fi "WINDOWTITLE eq AgentMesh*" >nul 2>&1
echo [STOP] Agent terminal windows closed.

echo [STOP] All done. Volumes and data preserved.
goto end


:: =============================================================================
:show_logs
:: =============================================================================
echo [LOGS] Streaming Docker logs (Ctrl+C to exit)...
docker compose -f docker-compose.demo.yml logs -f --tail=50
goto end


:: =============================================================================
:show_status
:: =============================================================================
echo.
echo  ── Docker Services ──────────────────────────────────────────────
docker compose -f docker-compose.demo.yml ps 2>nul || echo (no Docker demo running)
echo.
echo  ── Kafka Topics ─────────────────────────────────────────────────
docker compose -f docker-compose.demo.yml exec -T kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>nul || echo (Kafka not running)
echo.
echo  ── Ollama Status ────────────────────────────────────────────────
ollama list 2>nul || echo (Ollama not running)
goto end


:: =============================================================================
:ensure_env_demo
:: =============================================================================
if not exist "backend\.env.demo" (
    echo [SETUP] Creating backend\.env.demo ...
    (
        echo AICREDITS_API_KEY=
        echo USE_MOCK_LLM=false
        echo KAFKA_BOOTSTRAP_SERVERS=kafka:9092
        echo USE_REAL_KAFKA=false
        echo MAX_AGENT_TURNS=10
        echo CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:5173
    ) > backend\.env.demo
    echo [WARN] Add your AICREDITS_API_KEY to backend\.env.demo for cloud model fallback.
)
exit /b 0


:: =============================================================================
:print_urls_docker
:: =============================================================================
echo  ══════════════════════════════════════════════════════════
echo  ✅  AgentMesh Docker Demo is UP!
echo.
echo  📊  Research Dashboard   ^→  http://localhost
echo  🔌  FastAPI Docs         ^→  http://localhost:8000/docs
echo  📨  Kafka UI             ^→  http://localhost:8090
echo  🤖  Ollama (Supervisor)  ^→  http://localhost:11434
echo  🤖  Ollama (Specialist)  ^→  http://localhost:11435
echo  🤖  Ollama (Validator)   ^→  http://localhost:11436
echo  ══════════════════════════════════════════════════════════
echo.
echo  Useful commands:
echo    demo.bat inject  — inject 5 more benchmark tasks
echo    demo.bat logs    — stream all container logs
echo    demo.bat status  — check service health
echo    demo.bat stop    — shut everything down
exit /b 0


:: =============================================================================
:banner
:: =============================================================================
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║         AgentMesh — Multi-System Kafka Demo Launcher        ║
echo  ║  3 Ollama Models ^× Kafka Streams ^× Research Dashboard       ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
exit /b 0


:end
endlocal
