"""
Benchmark & Demonstration for Message Streams Topology (Kafka Pub/Sub Pattern).

Architecture:
┌────────────────────────────────────────────┐
│ Message Bus (Kafka / Partitioned Bus)      │
├────────────────────────────────────────────┤
│                                            │
│ Topic: tasks                               │
│  ├─ Partition 0: [Task1, Task2, Task3]    │
│  └─ Partition 1: [Task4, Task5, Task6]    │
│                                            │
│ Topic: routing-decisions                   │
│  └─ [Decision1, Decision2, ...]           │
│                                            │
│ Topic: specialist-results                  │
│  ├─ [Result1, Result2, ...]               │
│  └─ [Result3, Result4, ...]               │
│                                            │
│ Topic: validations                         │
│  └─ [Validation1, Validation2, ...]       │
│                                            │
└────────────────────────────────────────────┘

Agent subscriptions:
Supervisor:
  - Consumes: tasks
  - Produces: routing-decisions

Coding-Specialist:
  - Consumes: routing-decisions (filter: "coding")
  - Produces: specialist-results

Validator:
  - Consumes: specialist-results
  - Produces: validations
"""

import json
import os
import sys
import threading
import time

# Ensure backend and workspace root are in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.topologies.stream import (
    KafkaProducer,
    KafkaConsumer,
    SupervisorAgent,
    SpecialistAgent,
    ValidatorAgent,
    InMemoryKafkaBroker,
    HAS_REAL_KAFKA
)


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_message_stream_demo():
    print_banner("AGENTMESH: TOPOLOGY AS MESSAGE STREAMS (KAFKA PUB/SUB PATTERN)")
    print(f"[*] Real Kafka Client Installed: {HAS_REAL_KAFKA}")
    print("[*] Active Broker: Partitioned In-Memory Event Broker (Dual-Mode)")
    print("""
+--------------------------------------------------------+
| Message Bus (Kafka)                                    |
+--------------------------------------------------------+
| Topic: tasks                                           |
|  |- Partition 0: [Coding tasks]                        |
|  +- Partition 1: [Reasoning tasks]                     |
| Topic: routing-decisions  -> Supervisor routing stream |
| Topic: specialist-results -> Specialist workers stream |
| Topic: validations        -> Quality audit stream      |
+--------------------------------------------------------+
""")

    broker = InMemoryKafkaBroker.get_instance()
    model = "gpt-4o"

    print("[+] Instantiating Event-Driven Stream Agents:")
    supervisor = SupervisorAgent(model=model, broker=broker)
    coding_specialist = SpecialistAgent("coding", model=model, broker=broker)
    reasoning_specialist = SpecialistAgent("reasoning", model=model, broker=broker)
    validator = ValidatorAgent(model=model, broker=broker)

    print("    * SupervisorAgent         -> Subscribed to: ['tasks']")
    print("    * SpecialistAgent(coding) -> Subscribed to: ['routing-decisions'] (filter: coding)")
    print("    * SpecialistAgent(reason) -> Subscribed to: ['routing-decisions'] (filter: reasoning)")
    print("    * ValidatorAgent          -> Subscribed to: ['specialist-results']")

    print("\n[+] Launching Agents in Parallel Worker Threads:")
    supervisor_thread = threading.Thread(
        target=supervisor.run,
        name="supervisor-worker",
        daemon=True
    )
    coding_thread = threading.Thread(
        target=coding_specialist.run,
        name="coding-specialist-worker",
        daemon=True
    )
    reasoning_thread = threading.Thread(
        target=reasoning_specialist.run,
        name="reasoning-specialist-worker",
        daemon=True
    )
    validator_thread = threading.Thread(
        target=validator.run,
        name="validator-worker",
        daemon=True
    )

    supervisor_thread.start()
    coding_thread.start()
    reasoning_thread.start()
    validator_thread.start()

    print("    [+] supervisor_thread.start()")
    print("    [+] coding_thread.start()")
    print("    [+] reasoning_thread.start()")
    print("    [+] validator_thread.start()")

    time.sleep(0.1)

    # Initial tasks producer
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        broker=broker
    )

    # Consumer to monitor final validations stream
    validations_consumer = KafkaConsumer(
        'validations',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id='demo_audit_monitor',
        broker=broker,
        poll_timeout=0.2
    )

    tasks_to_send = [
        {
            "id": "fizzbuzz_1",
            "input": "Solve FizzBuzz in Python from 1 to 15",
            "partition": 0
        },
        {
            "id": "premise_logic_2",
            "input": "Analyze deductive consistency of premises A and B",
            "partition": 1
        }
    ]

    print("\n[+] Producing Initial Tasks to Topic 'tasks':")
    for t in tasks_to_send:
        print(f"    -> [Topic: tasks | Partition {t['partition']}] Task ID: '{t['id']}' | Input: '{t['input']}'")
        producer.send('tasks', {'id': t['id'], 'input': t['input']}, partition=t['partition'])
    producer.flush()

    print("\n[*] Processing Streams Across Topics...")
    print("    [tasks] -> [routing-decisions] -> [specialist-results] -> [validations]")

    collected_validations = []
    start_time = time.time()
    deadline = start_time + 5.0

    while len(collected_validations) < len(tasks_to_send) and time.time() < deadline:
        records = broker.poll_group("demo_audit_monitor", ["validations"], timeout=0.2, max_records=5)
        for r in records:
            val = r.value
            if isinstance(val, (bytes, bytearray)):
                val = json.loads(val.decode("utf-8"))
            collected_validations.append((r, val))

    elapsed = time.time() - start_time
    print(f"\n[+] Stream Processing Completed in {elapsed:.3f}s")
    print_banner("STREAM PIPELINE VALIDATION RESULTS")

    for record, val in collected_validations:
        status_symbol = "PASS" if val.get("is_valid") else "FAIL"
        print(f"[{status_symbol}] Task: {val.get('task_id')} | Specialist: {val.get('specialist_type')} | Partition: {record.partition} | Offset: {record.offset}")
        print(f"       Validation Reason: {val.get('reason')}")
        print(f"       Solution Output Preview:\n{val.get('output')[:180]}...\n")

    print_banner("MESSAGE BUS TOPIC & PARTITION TELEMETRY")
    stats = broker.get_topic_stats()
    for topic_name, tstats in stats.items():
        print(f"  * Topic: {topic_name:20s} | Partitions: {tstats['partitions']} | Total Messages: {tstats['total_messages']}")
        for part_id, size in tstats['partition_sizes'].items():
            print(f"      +- Partition {part_id}: {size} messages")

    # Graceful shutdown
    print("\n[*] Stopping Stream Agents & Cleaning Up Resources...")
    supervisor.stop()
    coding_specialist.stop()
    reasoning_specialist.stop()
    validator.stop()
    validations_consumer.close()
    producer.close()
    print("[+] All stream consumer threads gracefully shut down.")


if __name__ == "__main__":
    run_message_stream_demo()
