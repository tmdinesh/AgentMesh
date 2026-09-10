import json
import time
import threading
import pytest

from app.topologies.stream import (
    ConsumerRecord,
    InMemoryKafkaBroker,
    KafkaProducer,
    KafkaConsumer,
    SupervisorAgent,
    SpecialistAgent,
    ValidatorAgent,
    StreamPipeline,
    run_message_stream_pipeline,
    StreamTopology
)
from app.topologies import get_topology_instance
from app.services.agent_service import create_agent_team


@pytest.fixture(autouse=True)
def reset_broker():
    """Ensure a clean in-memory broker instance for each test."""
    InMemoryKafkaBroker.reset_instance()
    yield
    InMemoryKafkaBroker.reset_instance()


def test_in_memory_broker_partitioning():
    """Verify broker creates partitioned topics and assigns records properly."""
    broker = InMemoryKafkaBroker(default_partitions=2)
    broker.ensure_topic("tasks", num_partitions=2)

    # Produce to partition 0
    rec0 = broker.produce("tasks", b"Task 0", partition=0)
    assert rec0.topic == "tasks"
    assert rec0.partition == 0
    assert rec0.offset == 0

    # Produce to partition 1
    rec1 = broker.produce("tasks", b"Task 1", partition=1)
    assert rec1.partition == 1
    assert rec1.offset == 0

    # Round-robin without partition specified
    rec2 = broker.produce("tasks", b"Task 2")
    rec3 = broker.produce("tasks", b"Task 3")
    assert rec2.partition != rec3.partition

    stats = broker.get_topic_stats()
    assert stats["tasks"]["total_messages"] == 4
    assert stats["tasks"]["partitions"] == 2


def test_consumer_group_isolation():
    """Verify multiple consumer groups each read full stream independently."""
    broker = InMemoryKafkaBroker(default_partitions=1)
    broker.produce("routing-decisions", b'{"task_id": "t1", "route_to": "coding"}')
    broker.produce("routing-decisions", b'{"task_id": "t2", "route_to": "reasoning"}')

    # Group A
    group_a_records = broker.poll_group(group_id="group-a", topics=["routing-decisions"], timeout=0.1)
    assert len(group_a_records) == 2

    # Group B should also receive all 2 records independently
    group_b_records = broker.poll_group(group_id="group-b", topics=["routing-decisions"], timeout=0.1)
    assert len(group_b_records) == 2

    # Subsequent poll for Group A has 0 new records
    group_a_empty = broker.poll_group(group_id="group-a", topics=["routing-decisions"], timeout=0.1)
    assert len(group_a_empty) == 0


def test_kafka_producer_consumer_serialization():
    """Verify KafkaProducer serializes and KafkaConsumer deserializes JSON payloads."""
    producer = KafkaProducer(
        bootstrap_servers=["localhost:9092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    consumer = KafkaConsumer(
        "custom-topic",
        bootstrap_servers=["localhost:9092"],
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="test-consumer-group",
        poll_timeout=0.1
    )

    test_payload = {"id": "123", "command": "echo hello"}
    producer.send("custom-topic", test_payload)
    producer.flush()

    record = next(consumer)
    assert record.topic == "custom-topic"
    assert record.value == test_payload
    consumer.close()


def test_supervisor_agent_routing():
    """Verify SupervisorAgent consumes from 'tasks' and routes to 'routing-decisions'."""
    supervisor = SupervisorAgent(model="gpt-4o")

    # Start supervisor on background thread
    t = threading.Thread(target=supervisor.run, daemon=True)
    t.start()

    # Produce coding task to 'tasks'
    producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    producer.send("tasks", {"id": "task_code", "input": "Write a python script"})
    producer.flush()

    # Consume from 'routing-decisions'
    consumer = KafkaConsumer(
        "routing-decisions",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="test_supervisor_listener",
        poll_timeout=0.1
    )

    record = next(consumer)
    val = record.value
    assert val["task_id"] == "task_code"
    assert val["route_to"] == "coding"
    assert "script" in val["task_data"]

    supervisor.stop()
    consumer.close()


def test_specialist_agent_filtering_and_work():
    """Verify SpecialistAgent only processes tasks matching its specialist_type."""
    coding_spec = SpecialistAgent("coding", model="gpt-4o")
    reasoning_spec = SpecialistAgent("reasoning", model="gpt-4o")

    t_code = threading.Thread(target=coding_spec.run, daemon=True)
    t_reason = threading.Thread(target=reasoning_spec.run, daemon=True)
    t_code.start()
    t_reason.start()

    # Publish two decisions: one for coding, one for reasoning
    producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    producer.send("routing-decisions", {
        "task_id": "c_1",
        "route_to": "coding",
        "task_data": "Solve FizzBuzz"
    })
    producer.send("routing-decisions", {
        "task_id": "r_1",
        "route_to": "reasoning",
        "task_data": "Evaluate premise"
    })
    producer.flush()

    # Consumer listening on 'specialist-results'
    consumer = KafkaConsumer(
        "specialist-results",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="results_auditor",
        poll_timeout=0.2
    )

    results = []
    deadline = time.time() + 2.0
    for rec in consumer:
        results.append(rec.value)
        if len(results) >= 2 or time.time() > deadline:
            break

    task_ids = {r["task_id"] for r in results}
    assert "c_1" in task_ids
    assert "r_1" in task_ids

    coding_result = next(r for r in results if r["task_id"] == "c_1")
    assert coding_result["specialist_type"] == "coding"
    assert "fizzbuzz" in coding_result["output"].lower() or "python" in coding_result["output"].lower()

    coding_spec.stop()
    reasoning_spec.stop()
    consumer.close()


def test_validator_agent_validation():
    """Verify ValidatorAgent consumes from 'specialist-results' and emits 'validations'."""
    validator = ValidatorAgent(model="gpt-4o")
    t = threading.Thread(target=validator.run, daemon=True)
    t.start()

    producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    producer.send("specialist-results", {
        "task_id": "v_test",
        "specialist_type": "coding",
        "output": "def add(a, b):\n    return a + b\n# Well-tested solution"
    })
    producer.flush()

    consumer = KafkaConsumer(
        "validations",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="validation_auditor",
        poll_timeout=0.2
    )

    record = next(consumer)
    val = record.value
    assert val["task_id"] == "v_test"
    assert val["specialist_type"] == "coding"
    assert val["is_valid"] is True
    assert len(val["reason"]) > 0

    validator.stop()
    consumer.close()


def test_stream_pipeline_end_to_end():
    """Verify StreamPipeline completes full publish-route-process-validate workflow."""
    result = run_message_stream_pipeline(
        task_id="fizzbuzz_integration",
        task_input="Implement FizzBuzz in Python",
        model="gpt-4o",
        timeout=3.0
    )

    assert result["success"] is True
    assert result["task_id"] == "fizzbuzz_integration"
    assert result["validation"]["is_valid"] is True
    assert result["validation"]["specialist_type"] == "coding"

    stats = result["topic_stats"]
    assert stats["tasks"]["total_messages"] >= 1
    assert stats["routing-decisions"]["total_messages"] >= 1
    assert stats["specialist-results"]["total_messages"] >= 1
    assert stats["validations"]["total_messages"] >= 1


def test_stream_topology_graph_and_turn_planning():
    """Verify AgentMesh StreamTopology constraints, edges, and turn sequence."""
    agents = create_agent_team(num_agents=5)
    topology: StreamTopology = get_topology_instance("STREAM", agents)

    assert topology.name == "STREAM"
    sup = topology.supervisor
    val = topology.validator
    specs = topology.specialists

    # Graph edges
    edges = topology.get_graph_edges()
    for spec in specs:
        assert (sup.id, spec.id) in edges
        assert (spec.id, val.id) in edges
    assert (val.id, sup.id) in edges

    # Permissions
    for spec in specs:
        assert topology.is_allowed_communication(sup.id, spec.id) is True
        assert topology.is_allowed_communication(spec.id, val.id) is True
        assert topology.is_allowed_communication(spec.id, sup.id) is False  # Results go to Validator in Stream flow
    assert topology.is_allowed_communication(val.id, sup.id) is True

    # Lateral specialist <-> specialist is strictly disallowed
    if len(specs) >= 2:
        assert topology.is_allowed_communication(specs[0].id, specs[1].id) is False

    # Turn plan phases
    turn_0 = topology.plan_turn(0, [])
    assert turn_0[0][0].id == sup.id
    assert turn_0[0][1].id in [s.id for s in specs]

    turn_1 = topology.plan_turn(1, [])
    assert turn_1[0][0].id in [s.id for s in specs]
    assert turn_1[0][1].id == val.id

    turn_2 = topology.plan_turn(2, [])
    assert turn_2[0][0].id == val.id
    assert turn_2[0][1].id == sup.id
