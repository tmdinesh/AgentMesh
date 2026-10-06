\"\"\"
AgentMesh Multi-System Kafka Demo — Supervisor Agent Runner
============================================================
Run this on MACHINE A (with Ollama llama3:8b running locally).

Usage:
    set AGENT_1_MODEL=llama3:8b
    set KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    set USE_REAL_KAFKA=false
    python supervisor_runner.py
\"\"\"

import os, sys, logging
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [SUPERVISOR] %(message)s')
logger = logging.getLogger('supervisor_runner')

from app.topologies.stream import SupervisorAgent, InMemoryKafkaBroker

def main():
    model = os.getenv('AGENT_1_MODEL', 'llama3:8b')
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
    use_real = os.getenv('USE_REAL_KAFKA', 'false').lower() == 'true'
    logger.info(f'Supervisor | model={model} | kafka={kafka_servers} | real={use_real}')
    broker = None if use_real else InMemoryKafkaBroker.get_instance()
    supervisor = SupervisorAgent(model=model, bootstrap_servers=kafka_servers, broker=broker)
    try:
        supervisor.run()
    except KeyboardInterrupt:
        supervisor.stop()

if __name__ == '__main__':
    main()
