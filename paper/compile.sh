#!/usr/bin/env bash
# =============================================================================
# AgentMesh Research Paper Compilation Script (Linux/macOS)
# =============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================================================="
echo "Compiling AgentMesh Research Paper (LaTeX)"
echo "Target: main.pdf"
echo "============================================================================="

if ! command -v pdflatex &> /dev/null; then
    echo "[ERROR] pdflatex not found in PATH."
    echo "Install TeX Live or MacTeX, or compile via Overleaf/Docker."
    exit 1
fi

echo "[1/2] Running pdflatex pass 1..."
pdflatex -interaction=nonstopmode main.tex

echo "[2/2] Running pdflatex pass 2 (cross-references)..."
pdflatex -interaction=nonstopmode main.tex

if [ -f "main.pdf" ]; then
    echo "============================================================================="
    echo "[SUCCESS] Paper compiled successfully: paper/main.pdf"
    echo "============================================================================="
else
    echo "[ERROR] main.pdf was not produced."
    exit 1
fi
