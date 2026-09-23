@echo off
title AgentMesh - Multi-Agent Topology Benchmark Runner
cd /d "%~dp0"

echo ==============================================================================
echo            AgentMesh MAST Topology Lab - Experiment Orchestrator
echo ==============================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH. Please install Python 3.10+
    pause
    exit /b 1
)

python experiments/run_paper_experiments.py

echo.
echo ==============================================================================
echo All experiment routines have concluded.
echo Review the results in the results/ folder.
echo ==============================================================================
pause
