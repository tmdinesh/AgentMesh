@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: AgentMesh Kafka Demo Launcher (Windows)
:: Usage:
::   demo.bat          -> interactive menu
::   demo.bat 2        -> Option 2: Docker full stack (single click)
::   demo.bat 3        -> Option 3: Multi-terminal using local Ollama
::   demo.bat 4        -> Option 4: Multi-terminal using AICredits API key
::   demo.bat 5        -> Option 5: Single-task flow demo (choose Ollama or API)
::   demo.bat inject   -> inject tasks into running demo
::   demo.bat stop     -> stop all (Docker + Option 3 processes)
::   demo.bat logs     -> stream Docker logs
::   demo.bat status   -> check health
:: =============================================================================

title AgentMesh Kafka Demo
color 0A
cd /d "%~dp0"

call :banner

:: -- Route by first argument ---------------------------------------------------
set ARG=%~1
if "%ARG%"=="2"       goto option2
if "%ARG%"=="3"       goto option3
if "%ARG%"=="4"       goto option4
if "%ARG%"=="5"       goto option5
if "%ARG%"=="inject"  goto inject_tasks
if "%ARG%"=="stop"    goto stop_all
if "%ARG%"=="logs"    goto show_logs
if "%ARG%"=="status"  goto show_status
if "%ARG%"==""        goto menu

echo [ERROR] Unknown command: %ARG%
echo Usage: demo.bat [2^|3^|4^|5^|inject^|stop^|logs^|status]
exit /b 1

:: =============================================================================
:menu
:: =============================================================================
echo  Which demo mode do you want?
echo.
echo  [2]  OPTION 2 -- Docker Full Stack (recommended)
echo         Kafka + 3 Ollama + 4 Agents + Dashboard -- all in Docker
echo         Requires: Docker Desktop running
echo.
echo  [3]  OPTION 3 -- Multi-Terminal (shows architecture live)
echo         Opens 4 separate windows: Supervisor, Specialist, Validator, Injector
echo         Uses local Ollama models. Requires Python, Ollama, Docker Desktop
echo.
echo  [4]  OPTION 4 -- Multi-Terminal with API key
echo         Same 4 agent windows, using AICredits instead of local Ollama
echo         Requires Python, AICREDITS_API_KEY in .env, Docker Desktop
echo.
echo  [5]  OPTION 5 -- Single-task flow demo
echo         Starts the agents and injects one simple coding task automatically
echo         Choose Ollama or AICredits; watch each Kafka handoff in the windows
echo.
echo  [Q]  Quit
echo.
set /p CHOICE="  Enter choice [2/3/4/5/Q]: "

if /i "%CHOICE%"=="2" goto option2
if /i "%CHOICE%"=="3" goto option3
if /i "%CHOICE%"=="4" goto option4
if /i "%CHOICE%"=="5" goto option5
if /i "%CHOICE%"=="Q" goto end
echo Invalid choice. Try again.
goto menu


:: =============================================================================
:option2
:: =============================================================================
echo.
echo  +---------------------------------------------+
echo  ^|  OPTION 2 -- Docker Full Stack               ^|
echo  ^|  Kafka + 3 Ollama + Agents + Dashboard      ^|
echo  +---------------------------------------------+
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
docker compose -f docker-compose.demo.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list >nul 2>&1
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
set "DEMO_MODE=ollama"
set "DEMO_MODEL=llama3:latest"
set "AGENT_1_PROVIDER=ollama"
set "AGENT_1_BASE_URL=http://localhost:11434/v1"
set "AGENT_1_API_KEY=ollama"
goto multi_terminal


:: =============================================================================
:option4
:: =============================================================================
set "DEMO_MODE=api"
set "DEMO_MODEL=openai/gpt-oss-120b"
set "AGENT_1_PROVIDER=aicredits"
set "AGENT_1_BASE_URL=https://aicredits.in/v1"
set "AGENT_1_API_KEY="
if not defined AICREDITS_API_KEY (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do if /i "%%A"=="AICREDITS_API_KEY" set "AICREDITS_API_KEY=%%B"
)
if not defined AICREDITS_API_KEY (
    echo [ERROR] AICREDITS_API_KEY was not found in your environment or project .env file.
    echo         Add AICREDITS_API_KEY=your_key to .env, then run demo.bat 4 again.
    pause
    exit /b 1
)
if /i "%AICREDITS_API_KEY%"=="YOUR_AICREDITS_API_KEY_HERE" (
    echo [ERROR] Replace the placeholder AICREDITS_API_KEY in .env with your key.
    pause
    exit /b 1
)
goto multi_terminal


:: =============================================================================
:option5
:: =============================================================================
set "DEMO_SINGLE_TASK=true"
set "AGENTMESH_RUN_ID=%RANDOM%%RANDOM%"
set "AGENTMESH_TASKS_TOPIC=am_%AGENTMESH_RUN_ID%_tasks"
set "AGENTMESH_ROUTING_TOPIC=am_%AGENTMESH_RUN_ID%_routing"
set "AGENTMESH_RESULTS_TOPIC=am_%AGENTMESH_RUN_ID%_results"
set "AGENTMESH_VALIDATIONS_TOPIC=am_%AGENTMESH_RUN_ID%_validations"
echo.
echo  OPTION 5 -- Single-task flow demo
echo  [O] Local Ollama
echo  [A] AICredits API key
set /p SINGLE_MODE="  Choose model [O/A]: "
if /i "%SINGLE_MODE%"=="O" goto option3
if /i "%SINGLE_MODE%"=="A" goto option4
echo Invalid choice.
goto option5


:: =============================================================================
:multi_terminal
:: =============================================================================
echo.
echo  +-------------------------------------------------------------+
echo  ^|  Multi-Terminal -- %DEMO_MODE% mode                          ^|
echo  ^|  Opens 4 windows: Supervisor ^| Specialist ^| Validator ^| ...^|
echo  +-------------------------------------------------------------+
echo.

:: Check Python
where python >nul 2>&1 || (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

:: Check Ollama only for local-model Option 3
if /i not "%DEMO_MODE%"=="ollama" goto kafka_setup
where ollama >nul 2>&1 || (
    echo [ERROR] Ollama was not found. Install Ollama or choose Option 4 for API-key mode.
    pause & exit /b 1
)

:: Check model pulled
echo [CHECK] Verifying llama3:latest is available...
ollama list 2>nul | findstr /i "llama3" >nul 2>&1
if !errorlevel! neq 0 (
    echo [SETUP] Pulling llama3:latest -- this may take a few minutes...
    ollama pull llama3:latest
)
echo [OK] Model ready.

:: Separate processes must use a shared Kafka broker.
:kafka_setup
where docker >nul 2>&1 || (
    echo [ERROR] Docker Desktop is required to provide Kafka for the multi-terminal demo.
    pause & exit /b 1
)
docker info >nul 2>&1 || (
    echo [ERROR] Docker daemon is not running. Open Docker Desktop first.
    pause & exit /b 1
)
echo.
echo [SETUP] Starting Kafka and Kafka UI...
docker compose -f docker-compose.demo.yml up -d kafka kafka-ui
if !errorlevel! neq 0 (echo [ERROR] Could not start Kafka. & pause & exit /b 1)
set "KAFKA_BOOTSTRAP_SERVERS=localhost:9094"
set "USE_REAL_KAFKA=true"
set /a KAFKA_WAIT=0
:multi_kafka_wait
docker compose -f docker-compose.demo.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list >nul 2>&1
if !errorlevel! equ 0 goto multi_kafka_ready
if !KAFKA_WAIT! geq 90 (echo [ERROR] Kafka did not become ready in 90 seconds. & pause & exit /b 1)
timeout /t 3 /nobreak >nul
set /a KAFKA_WAIT+=3
goto multi_kafka_wait
:multi_kafka_ready
echo [OK] Shared Kafka broker is ready at localhost:9094.
if not defined AGENTMESH_TASKS_TOPIC set "AGENTMESH_TASKS_TOPIC=tasks"
if not defined AGENTMESH_ROUTING_TOPIC set "AGENTMESH_ROUTING_TOPIC=routing-decisions"
if not defined AGENTMESH_RESULTS_TOPIC set "AGENTMESH_RESULTS_TOPIC=specialist-results"
if not defined AGENTMESH_VALIDATIONS_TOPIC set "AGENTMESH_VALIDATIONS_TOPIC=validations"
for %%T in ("%AGENTMESH_TASKS_TOPIC%" "%AGENTMESH_ROUTING_TOPIC%" "%AGENTMESH_RESULTS_TOPIC%" "%AGENTMESH_VALIDATIONS_TOPIC%") do (
    set "TOPIC_NAME=%%~T"
    docker compose -f docker-compose.demo.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic !TOPIC_NAME! --partitions 2 --replication-factor 1 >nul 2>&1
    if errorlevel 1 (echo [ERROR] Could not create Kafka topic %%T. & pause & exit /b 1)
)
echo [OK] Kafka topics are ready: %AGENTMESH_TASKS_TOPIC%, %AGENTMESH_ROUTING_TOPIC%, %AGENTMESH_RESULTS_TOPIC%, %AGENTMESH_VALIDATIONS_TOPIC%.

:: Install backend dependencies
echo.
echo [SETUP] Installing backend Python dependencies...
cd backend
pip install -q -r requirements.txt
cd ..

:: Kill any leftover Option 3 processes
taskkill /f /fi "WINDOWTITLE eq AgentMesh Demo*" >nul 2>&1

echo.
echo [LAUNCH] Opening agent terminal windows...

:: Window 1 -- Supervisor
start "AgentMesh Demo - Supervisor (%DEMO_MODEL%)" cmd /k ^
  "color 0B && title AgentMesh Demo - Supervisor (%DEMO_MODEL%) && echo [SUPERVISOR] Consuming topic: tasks ^^> routing-decisions && echo. && cd backend && set AGENT_1_MODEL=%DEMO_MODEL% && set KAFKA_BOOTSTRAP_SERVERS=localhost:9094 && set USE_REAL_KAFKA=true && python supervisor_runner.py"

timeout /t 2 /nobreak >nul

:: Window 2 -- Specialist (coding)
start "AgentMesh Demo - Specialist-Coding (%DEMO_MODEL%)" cmd /k ^
  "color 0E && title AgentMesh Demo - Specialist-Coding (%DEMO_MODEL%) && echo [SPECIALIST] Consuming topic: routing-decisions ^^> specialist-results && echo. && cd backend && set AGENT_2_MODEL=%DEMO_MODEL% && set SPECIALIST_TYPE=coding && set KAFKA_BOOTSTRAP_SERVERS=localhost:9094 && set USE_REAL_KAFKA=true && python specialist_runner.py"

timeout /t 2 /nobreak >nul

:: Window 3 -- Specialist (reasoning)
start "AgentMesh Demo - Specialist-Reasoning (%DEMO_MODEL%)" cmd /k ^
  "color 06 && title AgentMesh Demo - Specialist-Reasoning (%DEMO_MODEL%) && echo [SPECIALIST] Consuming topic: routing-decisions ^^> specialist-results && echo. && cd backend && set AGENT_2_MODEL=%DEMO_MODEL% && set SPECIALIST_TYPE=reasoning && set KAFKA_BOOTSTRAP_SERVERS=localhost:9094 && set USE_REAL_KAFKA=true && python specialist_runner.py"

timeout /t 2 /nobreak >nul

:: Window 4 -- Validator
start "AgentMesh Demo - Validator (%DEMO_MODEL%)" cmd /k ^
  "color 0D && title AgentMesh Demo - Validator (%DEMO_MODEL%) && echo [VALIDATOR] Consuming topic: specialist-results ^^> validations && echo. && cd backend && set AGENT_3_MODEL=%DEMO_MODEL% && set KAFKA_BOOTSTRAP_SERVERS=localhost:9094 && set USE_REAL_KAFKA=true && python validator_runner.py"

echo.
echo  ==========================================================
echo  [OK]  4 Agent Windows Launched (%DEMO_MODE%)!
echo.
echo  Color Legend:
echo    [CYAN]    Supervisor       -- routes tasks to specialists
echo    [YELLOW]  Specialist Code  -- solves coding problems
echo    [ORANGE]  Specialist Reason-- solves logic problems
echo    [MAGENTA] Validator        -- validates and scores answers
echo  ==========================================================
echo.
if /i "%DEMO_SINGLE_TASK%"=="true" goto single_task_inject
echo  Inject tasks now? (waits 5s for agents to start)
set /p INJ="  [Y/N]: "
if /i "%INJ%"=="Y" (
    timeout /t 5 /nobreak >nul
    echo.
    echo [INJECT] Sending 5 benchmark tasks...
    start "AgentMesh Demo - Task Injector" cmd /k ^
      "color 0F && title AgentMesh Demo - Task Injector && echo Injecting tasks... && python task_injector.py && echo. && echo Done! Press any key to close. && pause"
)
goto end


:: =============================================================================
:single_task_inject
:: =============================================================================
echo [DEMO] One simple coding task will be sent after the agents start.
timeout /t 5 /nobreak >nul
start "AgentMesh Demo - Single Task Injector" cmd /k ^
  "color 0F && title AgentMesh Demo - Single Task Injector && echo Injecting one simple coding task... && cd backend && set TASK_INJECTOR_MODE=single && python task_injector.py && echo. && echo Done! Keep the agent windows open to monitor the flow. && pause"
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
    set "KAFKA_BOOTSTRAP_SERVERS=localhost:9094"
    set "USE_REAL_KAFKA=true"
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
taskkill /f /fi "WINDOWTITLE eq AgentMesh Demo*" >nul 2>&1
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
echo  -- Docker Services ----------------------------------------------
docker compose -f docker-compose.demo.yml ps 2>nul || echo (no Docker demo running)
echo.
echo  -- Kafka Topics -------------------------------------------------
docker compose -f docker-compose.demo.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>nul || echo (Kafka not running)
echo.
echo  -- Ollama Status ------------------------------------------------
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
echo  ==========================================================
echo  [OK]  AgentMesh Docker Demo is UP!
echo.
echo  [Dashboard]  Research Dashboard   -^>  http://localhost
echo  [API]  FastAPI Docs         -^>  http://localhost:8000/docs
echo  [Kafka]  Kafka UI             -^>  http://localhost:8090
echo  [Ollama]  Ollama (Supervisor)  -^>  http://localhost:11434
echo  [Ollama]  Ollama (Specialist)  -^>  http://localhost:11435
echo  [Ollama]  Ollama (Validator)   -^>  http://localhost:11436
echo  ==========================================================
echo.
echo  Useful commands:
echo    demo.bat inject  -- inject 5 more benchmark tasks
echo    demo.bat logs    -- stream all container logs
echo    demo.bat status  -- check service health
echo    demo.bat stop    -- shut everything down
exit /b 0


:: =============================================================================
:banner
:: =============================================================================
echo.
echo  +==============================================================+
echo  ^|         AgentMesh -- Multi-System Kafka Demo Launcher        ^|
echo  ^|  3 Ollama Models x Kafka Streams x Research Dashboard       ^|
echo  +==============================================================+
echo.
exit /b 0


:end
endlocal
