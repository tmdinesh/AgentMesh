@echo off
setlocal enabledelayedexpansion
title AgentMesh - Multi-Agent Topology Research Benchmark (65 Prompts)
cd /d "%~dp0"

:: ==============================================================================
:: AGENTMESH DISTRIBUTED BENCHMARK INSTRUCTIONS FOR TEAMMATES:
:: ------------------------------------------------------------------------------
:: 1. PREREQUISITES:
::    - Python 3.10+ installed and added to PATH
::    - API Key set in .env (AICREDITS_API_KEY=your_key)
::    - Dependencies installed: pip install -r requirements.txt
::
:: 2. RUNNING YOUR ASSIGNED PROMPT SLICE:
::    Option A - Direct Command Line (Fastest):
::      run_experiments.bat 8 27       <-- Teammate 1: Runs prompts 8 to 27
::      run_experiments.bat 28 46      <-- Teammate 2: Runs prompts 28 to 46
::      run_experiments.bat 47 65      <-- Teammate 3: Runs prompts 47 to 65
::
::    Option B - Interactive Wizard:
::      Double-click run_experiments.bat and follow the on-screen prompts.
::
:: 3. PUSHING RESULTS TO GITHUB:
::    Once your slice completes, commit and push to GitHub:
::      git add results/
::      git commit -m "feat(results): completed prompts X to Y"
::      git push
::    GitHub Actions will automatically merge your partition file into the
::    unified results/experiment_results.csv and update all paper figures.
:: ==============================================================================

echo ==============================================================================
echo            AgentMesh MAST Topology Lab - Experiment Orchestrator
echo          Full Research Benchmark: 65 Prompts x 5 Topologies (Distributed)
echo ==============================================================================
echo.
echo   QUICK INSTRUCTIONS FOR TEAMMATES:
echo   ----------------------------------------------------------------------------
echo   To execute your assigned prompt partition directly:
echo     run_experiments.bat 8 27       (Teammate 1: Prompts 8 to 27)
echo     run_experiments.bat 28 46      (Teammate 2: Prompts 28 to 46)
echo     run_experiments.bat 47 65      (Teammate 3: Prompts 47 to 65)
echo.
echo   When your run finishes, push results to GitHub:
echo     git add results/
echo     git commit -m "feat(results): completed prompts X to Y"
echo     git push
echo   GitHub Actions will automatically unify all data and recompute artifacts!
echo   ----------------------------------------------------------------------------
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check if first argument is a CLI flag (starts with "-")
if not "%~1"=="" (
    set "ARG1=%~1"
    set "FIRST_CHAR=!ARG1:~0,1!"
    if "!FIRST_CHAR!"=="-" (
        python experiments/run_paper_experiments.py %*
        goto :auto_merge
    )

    :: Check if positional arguments are numbers (e.g. run_experiments.bat 8 27 [reps])
    echo %~1| findstr /r "^[0-9][0-9]*$" >nul 2>&1
    if not errorlevel 1 (
        set "START_P=%~1"
        set "END_P=%~2"
        if "!END_P!"=="" set "END_P=%~1"
        set "REPS=5"
        if not "%~3"=="" set "REPS=%~3"
        set "MODELS=heterogeneous"
        goto :launch_positional
    )

    :: Otherwise, forward all arguments
    python experiments/run_paper_experiments.py %*
    goto :auto_merge
)

:interactive_menu
echo Benchmark Dataset : datasets/dataset.json (65 Prompts covering 14 MAST failure modes)
echo Target Topologies : STAR, CHAIN, TREE, MESH, EMERGENT (5 topologies)
echo Idempotent Mode   : ENABLED (skips already-completed runs automatically)
echo Auto-Partitioning : ENABLED (saves to results/partitions/ for collision-free git pushes)
echo.
echo ------------------------------------------------------------------------------
echo Select Research Benchmark Preset:
echo ------------------------------------------------------------------------------
echo   [1] Full Publication Benchmark (10 Replicates = 3,250 runs)
echo       - Maximum statistical power for LaTeX ANOVA, violin plots, and error bands
echo       - Est. Cost (gpt-oss-120b): ~$2.40 USD (~INR 240)
echo.
echo   [2] Standard Research Benchmark (5 Replicates = 1,625 runs) [RECOMMENDED]
echo       - Standard p ^< 0.05 statistical significance and confidence intervals
echo       - Est. Cost (gpt-oss-120b): ~$1.20 USD (~INR 120)
echo.
echo   [3] Fast Full-Dataset Pilot (1 Replicate = 325 runs)
echo       - Complete single-run coverage across all 65 failure modes
echo       - Est. Cost (gpt-oss-120b): ~$0.24 USD (~INR 24)
echo.
echo   [4] Custom Replicate Count (Enter 1 to 20 replicates)
echo.
echo   [5] Interactive Wizard (Select individual models, topologies, or simulation)
echo.
echo   [6] Merge Results Only (Unify partitions, deduplicate, update paper figures)
echo ------------------------------------------------------------------------------
set /p PRESET="Select preset [default: 2]: "
if "%PRESET%"=="" set PRESET=2

if "%PRESET%"=="6" (
    goto :auto_merge
)

if "%PRESET%"=="5" (
    python experiments/run_paper_experiments.py
    goto :auto_merge
)

set REPS=5
if "%PRESET%"=="1" set REPS=10
if "%PRESET%"=="2" set REPS=5
if "%PRESET%"=="3" set REPS=1
if "%PRESET%"=="4" (
    set /p REPS="Enter number of replicates (e.g., 5, 8, 10): "
    if "%REPS%"=="" set REPS=5
)

echo.
echo Select Model Architecture:
echo   [1] Heterogeneous Multi-LLM Team (GPT-OSS + Qwen3 + DeepSeek + Gemini) [DEFAULT & RECOMMENDED]
echo       - True multi-LLM collaboration: each agent role uses a distinct specialized model
echo   [2] Comparative Benchmark Suite: Heterogeneous Team vs Homogeneous Baselines
echo   [3] Homogeneous Baseline: OpenAI gpt-oss-120b only
echo   [4] Homogeneous Baseline: DeepSeek V3.2 only
echo   [5] Homogeneous Baseline: Qwen3 30B Instruct only
set /p MCHOICE="Select model architecture [default: 1]: "
if "%MCHOICE%"=="" set MCHOICE=1

set MODELS=heterogeneous
if "%MCHOICE%"=="1" set MODELS=heterogeneous
if "%MCHOICE%"=="2" set MODELS=heterogeneous,gpt_oss_120b,deepseek_v3_2
if "%MCHOICE%"=="3" set MODELS=gpt_oss_120b
if "%MCHOICE%"=="4" set MODELS=deepseek_v3_2
if "%MCHOICE%"=="5" set MODELS=qwen3_30b

echo.
echo ------------------------------------------------------------------------------
echo Distributed Benchmark Slicing (Dataset has 65 prompts):
echo ------------------------------------------------------------------------------
echo Divide prompts across multiple machines or friends:
echo   - Example split across 3 teammates:
echo       Teammate 1: Prompts 8 to 27
echo       Teammate 2: Prompts 28 to 46
echo       Teammate 3: Prompts 47 to 65
echo ------------------------------------------------------------------------------
set /p START_P="Enter Start Prompt Number [1-65, default: 1]: "
if "%START_P%"=="" set START_P=1

set /p END_P="Enter End Prompt Number   [1-65, default: 65]: "
if "%END_P%"=="" set END_P=65

echo.
echo ==============================================================================
echo Launching Benchmark Slice:
echo   Prompt Range : #%START_P% to #%END_P%
echo   Dataset      : datasets/dataset.json (65 Prompts)
echo   Topologies   : STAR, CHAIN, TREE, MESH, EMERGENT
echo   Model(s)     : %MODELS%
echo   Replicates   : %REPS%
echo ==============================================================================
echo.

python experiments/run_paper_experiments.py --non-interactive --dataset datasets/dataset.json --models %MODELS% --topologies STAR,CHAIN,TREE,MESH,EMERGENT --replicates %REPS% --start-prompt %START_P% --end-prompt %END_P%
goto :auto_merge

:launch_positional
echo.
echo ==============================================================================
echo Launching Positional Benchmark Slice:
echo   Prompt Range : #%START_P% to #%END_P%
echo   Dataset      : datasets/dataset.json (65 Prompts)
echo   Topologies   : STAR, CHAIN, TREE, MESH, EMERGENT
echo   Model(s)     : %MODELS%
echo   Replicates   : %REPS%
echo ==============================================================================
echo.

python experiments/run_paper_experiments.py --non-interactive --dataset datasets/dataset.json --models %MODELS% --topologies STAR,CHAIN,TREE,MESH,EMERGENT --replicates %REPS% --start-prompt %START_P% --end-prompt %END_P%
goto :auto_merge

:auto_merge
echo.
echo ==============================================================================
echo Unifying benchmark partitions and regenerating paper artifacts...
echo ==============================================================================
python experiments/merge_results.py

:end
echo.
echo ==============================================================================
echo Experiment routine concluded.
echo Results and generated artifacts:
echo   - CSV Data     : results/experiment_results.csv
echo   - Partitions   : results/partitions/
echo   - Traces JSONL : results/traces.jsonl
echo   - Transcripts  : results/transcripts/
echo   - Paper Stats  : results/statistical_summary.json
echo   - Figures      : results/figures/
echo   - LaTeX Tables : results/paper_results_section.md
echo ==============================================================================
echo.
echo NEXT STEP: Push your results to GitHub so they automatically merge:
echo   git add results/
echo   git commit -m "feat(results): completed prompts slice"
echo   git push
echo ==============================================================================
pause
