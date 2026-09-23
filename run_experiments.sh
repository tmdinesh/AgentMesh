#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=============================================================================="
echo "           AgentMesh MAST Topology Lab - Experiment Orchestrator"
echo "=============================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[ERROR] Python 3 is not found in PATH."
        exit 1
    else
        PYTHON_CMD=python
    fi
else
    PYTHON_CMD=python3
fi

$PYTHON_CMD experiments/run_paper_experiments.py

echo ""
echo "=============================================================================="
echo "All experiment routines have concluded. Review results in results/."
echo "=============================================================================="
