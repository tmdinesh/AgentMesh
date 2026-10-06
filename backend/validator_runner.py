import os, sys, logging
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))
logging.basicConfig(level=logging.INFO, format='%(asctime)s [VALIDATOR] %(message)s')
logger = logging.getLogger('validator_runner')
from app.topologies.stream import ValidatorAgent, InMemoryKafkaBroker
def main():
    model = os.getenv('AGENT_3_MODEL', 'phi3:medium')
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
    use_real = os.getenv('USE_REAL_KAFKA', 'false').lower() == 'true'
    logger.info(f'Validator | model={model} | kafka={kafka_servers} | real={use_real}')
    broker = None if use_real else InMemoryKafkaBroker.get_instance()
    validator = ValidatorAgent(model=model, bootstrap_servers=kafka_servers, broker=broker)
    try:
        validator.run()
    except KeyboardInterrupt:
        validator.stop()
if __name__ == '__main__':
    main()
