@echo off
setlocal
echo =============================================================================
echo Compiling AgentMesh Research Paper (LaTeX)
echo Target: main.pdf
echo =============================================================================

where pdflatex >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pdflatex not found in PATH.
    echo Please install MiKTeX or TeX Live, or upload to Overleaf.
    pause
    exit /b 1
)

echo [1/2] Running pdflatex pass 1...
pdflatex -interaction=nonstopmode main.tex
if %errorlevel% neq 0 (
    echo [ERROR] pdflatex pass 1 failed. Check main.log for details.
    pause
    exit /b 1
)

echo [2/2] Running pdflatex pass 2 (resolving cross-references)...
pdflatex -interaction=nonstopmode main.tex

if exist main.pdf (
    echo =============================================================================
    echo [SUCCESS] Paper compiled successfully: paper/main.pdf
    echo =============================================================================
) else (
    echo [ERROR] main.pdf was not produced.
)
