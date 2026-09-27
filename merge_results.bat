@echo off
title AgentMesh - Results Auto-Merger
cd /d "%~dp0"

echo ==============================================================================
echo            AgentMesh MAST Benchmark - Results Auto-Merger
echo ==============================================================================
echo.
python experiments/merge_results.py
echo.
pause
