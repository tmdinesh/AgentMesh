"""
AgentMesh — Kafka Benchmark Task Injector (Backend Service)
Injects benchmark reasoning and coding tasks into the 'tasks' topic.
Compatible with InMemoryKafkaBroker (local) and real Apache Kafka.
"""
import os
import sys
import json
import time
import logging
from pathlib import Path

# Support running from backend/ or project root
CUR_DIR = Path(__file__).resolve().parent
if str(CUR_DIR) not in sys.path:
    sys.path.insert(0, str(CUR_DIR))
if (CUR_DIR / '..' / 'backend').exists() and str(CUR_DIR / '..' / 'backend') not in sys.path:
    sys.path.insert(0, str((CUR_DIR / '..' / 'backend').resolve()))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [INJECTOR] %(message)s')
logger = logging.getLogger('task_injector')

from app.topologies.stream import KafkaProducer, InMemoryKafkaBroker

DEMO_TASKS = [
    {
        'id': 'task_001',
        'category': 'coding',
        'input': 'Solve FizzBuzz in Python for N=20 with detailed comments and time complexity analysis.'
    },
    {
        'id': 'task_002',
        'category': 'reasoning',
        'input': 'Knights and Knaves Island: A says "B is a knave". B says "A and I are of different types". Who is who? Provide step-by-step logic.'
    },
    {
        'id': 'task_003',
        'category': 'coding',
        'input': 'Design a sliding window rate limiter algorithm in Python for a high-traffic REST API with edge case handling.'
    },
    {
        'id': 'task_004',
        'category': 'reasoning',
        'input': 'Explain the CAP theorem with a practical distributed systems example comparing DynamoDB vs Cassandra.'
    },
    {
        'id': 'task_005',
        'category': 'coding',
        'input': 'Write an optimal binary search implementation handling rotated sorted arrays with duplicates.'
    },
]


def main():
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
    use_real = os.getenv('USE_REAL_KAFKA', 'false').lower() == 'true'
    delay = float(os.getenv('TASK_INJECT_DELAY', '2.5'))

    broker = None if use_real else InMemoryKafkaBroker.get_instance()
    producer = KafkaProducer(
        bootstrap_servers=kafka_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        broker=broker
    )

    logger.info(f"Injecting {len(DEMO_TASKS)} tasks (kafka={kafka_servers}, real={use_real})")
    for task in DEMO_TASKS:
        producer.send('tasks', task)
        producer.flush()
        logger.info(f"Injected: {task['id']} [{task.get('category')}] — {task['input'][:65]}...")
        time.sleep(delay)

    producer.close()
    logger.info("All demo benchmark tasks successfully injected into topic 'tasks'.")


if __name__ == '__main__':
    main()
