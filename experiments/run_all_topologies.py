"""
Runner entrypoint redirecting to run_paper_experiments.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from experiments.run_paper_experiments import main

if __name__ == "__main__":
    asyncio.run(main())
