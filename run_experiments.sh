#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=============================================================================="
echo "           AgentMesh MAST Topology Lab - Experiment Orchestrator"
echo "         Full Research Benchmark: 65 Prompts x 5 Topologies (Distributed)"
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

START_P=${1:-1}
END_P=${2:-65}
REPS=${3:-5}
MODELS=${4:-heterogeneous}

# If first argument starts with "-", pass all arguments directly to python
if [[ "$1" == -* ]]; then
    $PYTHON_CMD experiments/run_paper_experiments.py "$@"
else
    echo "Launching Benchmark Slice: Prompts #$START_P to #$END_P (Replicates: $REPS)..."
    $PYTHON_CMD experiments/run_paper_experiments.py \
        --non-interactive \
        --dataset datasets/dataset.json \
        --models "$MODELS" \
        --topologies STAR,CHAIN,TREE,MESH,EMERGENT \
        --replicates "$REPS" \
        --start-prompt "$START_P" \
        --end-prompt "$END_P"
fi

echo ""
echo "[*] Unifying benchmark partitions and regenerating paper artifacts..."
$PYTHON_CMD experiments/merge_results.py

echo ""
echo "=============================================================================="
echo "Experiment routine concluded. Review unified results in results/."
echo "=============================================================================="
