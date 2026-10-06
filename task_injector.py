"""
AgentMesh — Kafka Benchmark Task Injector (Root CLI wrapper)
Injects benchmark reasoning and coding tasks into the 'tasks' topic.
"""
import sys
from pathlib import Path

# Add backend directory to path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from task_injector import main

if __name__ == '__main__':
    main()
