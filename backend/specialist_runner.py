import os, sys, logging
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))
logging.basicConfig(level=logging.INFO, format='%(asctime)s [SPECIALIST] %(message)s')
logger = logging.getLogger('specialist_runner')
from app.topologies.stream import SpecialistAgent, InMemoryKafkaBroker
def main():
    model = os.getenv('AGENT_2_MODEL', 'mistral:7b')
    stype = os.getenv('SPECIALIST_TYPE', 'coding')
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
    use_real = os.getenv('USE_REAL_KAFKA', 'false').lower() == 'true'
    logger.info(f'Specialist:{stype} | model={model} | kafka={kafka_servers} | real={use_real}')
    broker = None if use_real else InMemoryKafkaBroker.get_instance()
    specialist = SpecialistAgent(specialist_type=stype, model=model, bootstrap_servers=kafka_servers, broker=broker)
    try:
        specialist.run()
    except KeyboardInterrupt:
        specialist.stop()
if __name__ == '__main__':
    main()
