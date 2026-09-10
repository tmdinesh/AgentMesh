"""
Topology as Message Streams (Kafka / Event-Driven Pub-Sub Architecture).

Architecture:
┌────────────────────────────────────────────────────────┐
│ Message Bus (Kafka / In-Memory Partitioned Broker)     │
├────────────────────────────────────────────────────────┤
│                                                        │
│ Topic: tasks                                           │
│  ├─ Partition 0: [Task1, Task2, Task3]                 │
│  └─ Partition 1: [Task4, Task5, Task6]                 │
│                                                        │
│ Topic: routing-decisions                               │
│  └─ [Decision1, Decision2, ...]                        │
│                                                        │
│ Topic: specialist-results                              │
│  ├─ [Result1, Result2, ...]                            │
│  └─ [Result3, Result4, ...]                            │
│                                                        │
│ Topic: validations                                     │
│  └─ [Validation1, Validation2, ...]                    │
│                                                        │
└────────────────────────────────────────────────────────┘

Agent Subscriptions:
- SupervisorAgent:
    - Consumes: tasks
    - Produces: routing-decisions
- SpecialistAgent:
    - Consumes: routing-decisions (filter: "coding", "reasoning", etc.)
    - Produces: specialist-results
- ValidatorAgent:
    - Consumes: specialist-results
    - Produces: validations
"""

from __future__ import annotations

import collections
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from app.topologies.actor_system import BaseLLMClient, get_llm_client
from app.topologies.base import AgentInfo, BaseTopology

logger = logging.getLogger(__name__)

# Try importing real kafka if present in environment
try:
    import kafka as real_kafka
    HAS_REAL_KAFKA = True
except ImportError:
    real_kafka = None
    HAS_REAL_KAFKA = False


# ==============================================================================
# 1. Consumer Record Data Structure
# ==============================================================================

@dataclass(frozen=True)
class ConsumerRecord:
    """
    Represents an immutable record returned by a Kafka consumer,
    mirroring kafka-python's ConsumerRecord.
    """
    topic: str
    partition: int
    offset: int
    timestamp: float
    key: Optional[bytes]
    value: Any
    headers: List[Tuple[str, bytes]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp,
            "key": self.key.decode("utf-8") if isinstance(self.key, (bytes, bytearray)) else self.key,
            "value": self.value,
        }


# ==============================================================================
# 2. In-Memory Partitioned Event Broker
# ==============================================================================

class _TopicPartition:
    """Represents a single partition within a topic."""

    def __init__(self, topic: str, partition_id: int):
        self.topic = topic
        self.partition_id = partition_id
        self.records: List[ConsumerRecord] = []
        self._lock = threading.Lock()

    def append(self, key: Optional[bytes], value: Any) -> ConsumerRecord:
        with self._lock:
            offset = len(self.records)
            rec = ConsumerRecord(
                topic=self.topic,
                partition=self.partition_id,
                offset=offset,
                timestamp=time.time(),
                key=key,
                value=value
            )
            self.records.append(rec)
            return rec

    def get_records_since(self, offset: int) -> List[ConsumerRecord]:
        with self._lock:
            if offset < len(self.records):
                return list(self.records[offset:])
            return []


class InMemoryKafkaBroker:
    """
    In-memory partitioned message broker replicating Apache Kafka behavior.
    Features:
    - Multiple topics with customizable partitions (e.g. Partition 0, Partition 1).
    - Partitioning: Explicit partition, hash-based on key, or round-robin.
    - Consumer groups: Independent group offsets.
    - Thread-safe blocking wait/notify via threading.Condition.
    """

    _instance: Optional[InMemoryKafkaBroker] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> InMemoryKafkaBroker:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = cls()

    def __init__(self, default_partitions: int = 2):
        self.default_partitions = max(1, default_partitions)
        self.topics: Dict[str, List[_TopicPartition]] = {}
        self.group_offsets: Dict[str, Dict[Tuple[str, int], int]] = collections.defaultdict(dict)
        self.round_robin_counter: Dict[str, int] = collections.defaultdict(int)
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._is_shutdown = False

        # Pre-seed standard topics from user diagram
        for t in ["tasks", "routing-decisions", "specialist-results", "validations"]:
            self.ensure_topic(t)

    def ensure_topic(self, topic: str, num_partitions: Optional[int] = None) -> List[_TopicPartition]:
        with self._lock:
            if topic not in self.topics:
                n = num_partitions or self.default_partitions
                self.topics[topic] = [_TopicPartition(topic, i) for i in range(n)]
            return self.topics[topic]

    def produce(
        self,
        topic: str,
        value_bytes: bytes,
        key_bytes: Optional[bytes] = None,
        partition: Optional[int] = None
    ) -> ConsumerRecord:
        with self._condition:
            if self._is_shutdown:
                raise RuntimeError("Broker is shut down.")

            partitions = self.ensure_topic(topic)
            n_parts = len(partitions)

            if partition is not None:
                target_part_id = partition % n_parts
            elif key_bytes is not None:
                target_part_id = abs(hash(key_bytes)) % n_parts
            else:
                target_part_id = self.round_robin_counter[topic] % n_parts
                self.round_robin_counter[topic] += 1

            target_part = partitions[target_part_id]
            rec = target_part.append(key_bytes, value_bytes)

            # Notify waiting consumers
            self._condition.notify_all()
            return rec

    def poll_group(
        self,
        group_id: str,
        topics: List[str],
        timeout: float = 0.5,
        max_records: int = 100
    ) -> List[ConsumerRecord]:
        """Polls records for a consumer group across subscribed topics."""
        deadline = time.time() + timeout
        results: List[ConsumerRecord] = []

        with self._condition:
            while not self._is_shutdown:
                # Scan across topics
                for topic in topics:
                    partitions = self.ensure_topic(topic)
                    for part in partitions:
                        key = (topic, part.partition_id)
                        current_offset = self.group_offsets[group_id].get(key, 0)
                        records = part.get_records_since(current_offset)
                        if records:
                            needed = max_records - len(results)
                            batch = records[:needed]
                            results.extend(batch)
                            self.group_offsets[group_id][key] = current_offset + len(batch)
                            if len(results) >= max_records:
                                return results

                if results:
                    return results

                remaining = deadline - time.time()
                if remaining <= 0:
                    break

                self._condition.wait(timeout=min(remaining, 0.2))

        return results

    def shutdown(self) -> None:
        with self._condition:
            self._is_shutdown = True
            self._condition.notify_all()

    def get_topic_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = {}
            for t, parts in self.topics.items():
                stats[t] = {
                    "partitions": len(parts),
                    "total_messages": sum(len(p.records) for p in parts),
                    "partition_sizes": {p.partition_id: len(p.records) for p in parts}
                }
            return stats


# ==============================================================================
# 3. KafkaProducer and KafkaConsumer Implementations
# ==============================================================================

class KafkaProducer:
    """
    Kafka Producer compatible with kafka-python's KafkaProducer.
    Operates in dual-mode:
    - Dispatches to InMemoryKafkaBroker by default or when broker is unreachable.
    - If real kafka is available and use_real=True, delegates to live Kafka cluster.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[Union[str, List[str]]] = None,
        value_serializer: Optional[Callable[[Any], bytes]] = None,
        key_serializer: Optional[Callable[[Any], bytes]] = None,
        broker: Optional[InMemoryKafkaBroker] = None,
        use_real: bool = False
    ):
        self.bootstrap_servers = bootstrap_servers or ["localhost:9092"]
        self.value_serializer = value_serializer or (lambda v: json.dumps(v).encode("utf-8") if isinstance(v, (dict, list)) else str(v).encode("utf-8"))
        self.key_serializer = key_serializer
        self.broker = broker or InMemoryKafkaBroker.get_instance()
        self.use_real = use_real and HAS_REAL_KAFKA
        self._real_producer = None

        if self.use_real and real_kafka is not None:
            try:
                self._real_producer = real_kafka.KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=self.value_serializer,
                    key_serializer=self.key_serializer,
                    request_timeout_ms=2000
                )
            except Exception as err:
                logger.warning(f"Real Kafka unavailable ({err}), falling back to InMemoryKafkaBroker.")
                self.use_real = False

    def send(
        self,
        topic: str,
        value: Any,
        key: Optional[Any] = None,
        partition: Optional[int] = None
    ) -> Any:
        """Publishes a message to a topic (non-blocking)."""
        if self.use_real and self._real_producer:
            return self._real_producer.send(topic, value=value, key=key, partition=partition)

        val_bytes = self.value_serializer(value) if self.value_serializer else (value if isinstance(value, bytes) else str(value).encode("utf-8"))
        key_bytes = None
        if key is not None:
            key_bytes = self.key_serializer(key) if self.key_serializer else (key if isinstance(key, bytes) else str(key).encode("utf-8"))

        rec = self.broker.produce(topic, val_bytes, key_bytes, partition=partition)
        return _CompletedFuture(rec)

    def flush(self, timeout: Optional[float] = None) -> None:
        """Flushes buffered records."""
        if self.use_real and self._real_producer:
            self._real_producer.flush(timeout=timeout)

    def close(self, timeout: Optional[float] = None) -> None:
        """Closes the producer."""
        if self.use_real and self._real_producer:
            self._real_producer.close(timeout=timeout)


class _CompletedFuture:
    """Mock Future returned by in-memory producer send()."""

    def __init__(self, record: ConsumerRecord):
        self._record = record

    def get(self, timeout: Optional[float] = None) -> ConsumerRecord:
        return self._record


class KafkaConsumer:
    """
    Kafka Consumer compatible with kafka-python's KafkaConsumer.
    Supports:
    - Blocking iteration: `for message in consumer:`
    - Deserialization: `value_deserializer`
    - Consumer groups: `group_id`
    - Topic subscriptions
    - Polling and graceful closure
    """

    def __init__(
        self,
        *topics: str,
        bootstrap_servers: Optional[Union[str, List[str]]] = None,
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        key_deserializer: Optional[Callable[[bytes], Any]] = None,
        group_id: Optional[str] = None,
        broker: Optional[InMemoryKafkaBroker] = None,
        use_real: bool = False,
        poll_timeout: float = 0.5
    ):
        self.topics = list(topics)
        self.bootstrap_servers = bootstrap_servers or ["localhost:9092"]
        self.value_deserializer = value_deserializer or (lambda m: json.loads(m.decode("utf-8")) if m else None)
        self.key_deserializer = key_deserializer
        self.group_id = group_id or f"group_{int(time.time() * 1000)}"
        self.broker = broker or InMemoryKafkaBroker.get_instance()
        self.poll_timeout = poll_timeout
        self.use_real = use_real and HAS_REAL_KAFKA
        self._closed = False
        self._real_consumer = None

        if self.use_real and real_kafka is not None:
            try:
                self._real_consumer = real_kafka.KafkaConsumer(
                    *self.topics,
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=self.value_deserializer,
                    key_deserializer=self.key_deserializer,
                    group_id=self.group_id,
                    consumer_timeout_ms=1000
                )
            except Exception as err:
                logger.warning(f"Real Kafka consumer unavailable ({err}), falling back to InMemoryKafkaBroker.")
                self.use_real = False

    def __iter__(self) -> Iterator[ConsumerRecord]:
        return self

    def __next__(self) -> ConsumerRecord:
        while not self._closed:
            if self.use_real and self._real_consumer:
                try:
                    return next(self._real_consumer)
                except StopIteration:
                    if self._closed:
                        raise StopIteration
                    continue

            records = self.broker.poll_group(
                group_id=self.group_id,
                topics=self.topics,
                timeout=self.poll_timeout,
                max_records=1
            )
            if records:
                raw_rec = records[0]
                val = raw_rec.value
                if self.value_deserializer and isinstance(val, (bytes, bytearray)):
                    try:
                        val = self.value_deserializer(val)
                    except Exception as err:
                        logger.warning(f"Deserialization error on {raw_rec.topic}: {err}")

                return ConsumerRecord(
                    topic=raw_rec.topic,
                    partition=raw_rec.partition,
                    offset=raw_rec.offset,
                    timestamp=raw_rec.timestamp,
                    key=raw_rec.key,
                    value=val
                )

        raise StopIteration

    def poll(self, timeout_ms: int = 500, max_records: int = 100) -> Dict[str, List[ConsumerRecord]]:
        """Polls for records, returning a dict keyed by topic."""
        timeout_sec = timeout_ms / 1000.0
        records = self.broker.poll_group(
            group_id=self.group_id,
            topics=self.topics,
            timeout=timeout_sec,
            max_records=max_records
        )
        grouped: Dict[str, List[ConsumerRecord]] = collections.defaultdict(list)
        for r in records:
            val = r.value
            if self.value_deserializer and isinstance(val, (bytes, bytearray)):
                try:
                    val = self.value_deserializer(val)
                except Exception:
                    pass
            grouped[r.topic].append(
                ConsumerRecord(
                    topic=r.topic,
                    partition=r.partition,
                    offset=r.offset,
                    timestamp=r.timestamp,
                    key=r.key,
                    value=val
                )
            )
        return dict(grouped)

    def close(self) -> None:
        """Signals the consumer to gracefully stop."""
        self._closed = True
        if self.use_real and self._real_consumer:
            try:
                self._real_consumer.close()
            except Exception:
                pass


# ==============================================================================
# 4. Stream Agents (Supervisor, Specialist, Validator)
# ==============================================================================

class SupervisorAgent:
    """
    Supervisor that consumes task requests from 'tasks' and routes them
    to 'routing-decisions'.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        bootstrap_servers: Optional[List[str]] = None,
        broker: Optional[InMemoryKafkaBroker] = None
    ):
        self.model = model
        self.llm_client: BaseLLMClient = get_llm_client(model)
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            broker=broker
        )
        self.consumer = KafkaConsumer(
            "tasks",
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="supervisor",
            broker=broker
        )
        self.processed_tasks: List[str] = []
        self._running = False

    def run(self) -> None:
        """Main loop: consume tasks, route them."""
        self._running = True
        logger.info("[SupervisorAgent] Starting consumption loop on topic 'tasks'...")

        for message in self.consumer:
            if not self._running:
                break
            task = message.value
            task_id = task.get("id", f"task_{int(time.time()*1000)}")
            task_input = task.get("input", "")

            # Make routing decision
            decision = self.llm_client.call(
                system="Route this task. Return 'coding' or 'reasoning'.",
                user=task_input
            )

            routing_key = "coding" if "coding" in decision.lower() else "reasoning"

            # Publish routing decision
            self.producer.send("routing-decisions", {
                "task_id": task_id,
                "route_to": routing_key,
                "task_data": task_input
            })

            # Non-blocking send (async)
            self.producer.flush()
            self.processed_tasks.append(task_id)

    def stop(self) -> None:
        """Stops the agent and closes the consumer."""
        self._running = False
        self.consumer.close()
        self.producer.close()


class SpecialistAgent:
    """
    Specialist that consumes routing decisions from 'routing-decisions',
    processes work for matching specialist_type, and publishes to 'specialist-results'.
    """

    def __init__(
        self,
        specialist_type: str,
        model: str = "gpt-4o",
        bootstrap_servers: Optional[List[str]] = None,
        broker: Optional[InMemoryKafkaBroker] = None
    ):
        self.type = specialist_type
        self.model = model
        self.llm_client: BaseLLMClient = get_llm_client(model)
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            broker=broker
        )
        self.consumer = KafkaConsumer(
            "routing-decisions",
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"specialist-{specialist_type}",
            broker=broker
        )
        self.completed_tasks: List[str] = []
        self._running = False

    def run(self) -> None:
        """Main loop: consume routing decisions, process work."""
        self._running = True
        logger.info(f"[SpecialistAgent:{self.type}] Starting consumption on 'routing-decisions'...")

        for message in self.consumer:
            if not self._running:
                break
            routing = message.value

            # Filter: only process if routed to this specialist
            if routing.get("route_to") != self.type:
                continue

            # Do the work
            output = self.llm_client.call(
                system=f"You are a {self.type} specialist",
                user=routing.get("task_data", "")
            )

            # Publish result
            self.producer.send("specialist-results", {
                "task_id": routing.get("task_id"),
                "specialist_type": self.type,
                "output": output
            })

            self.producer.flush()
            self.completed_tasks.append(routing.get("task_id", ""))

    def stop(self) -> None:
        """Stops the agent and closes the consumer."""
        self._running = False
        self.consumer.close()
        self.producer.close()


class ValidatorAgent:
    """
    Validator that consumes from 'specialist-results',
    audits output correctness against acceptance criteria, and publishes to 'validations'.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        criteria: Optional[str] = None,
        bootstrap_servers: Optional[List[str]] = None,
        broker: Optional[InMemoryKafkaBroker] = None
    ):
        self.model = model
        self.criteria = criteria or "Correctness, constraint adherence, completeness, and logical soundness."
        self.llm_client: BaseLLMClient = get_llm_client(model)
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            broker=broker
        )
        self.consumer = KafkaConsumer(
            "specialist-results",
            bootstrap_servers=bootstrap_servers or ["localhost:9092"],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="validator",
            broker=broker
        )
        self.validated_tasks: List[Dict[str, Any]] = []
        self._running = False

    def run(self) -> None:
        """Main loop: consume specialist results, validate output."""
        self._running = True
        logger.info("[ValidatorAgent] Starting consumption on 'specialist-results'...")

        for message in self.consumer:
            if not self._running:
                break
            result = message.value

            output = result.get("output", "")
            task_id = result.get("task_id", "unknown")
            spec_type = result.get("specialist_type", "unknown")

            # Validate output via LLM
            validation = self.llm_client.call(
                system=f"You are the Validator. Evaluate if the output meets criteria: '{self.criteria}'. Reply 'YES' or 'NO' with diagnostic reasoning.",
                user=output
            )

            is_valid = "yes" in validation.lower()

            # Publish validation verdict
            payload = {
                "task_id": task_id,
                "specialist_type": spec_type,
                "is_valid": is_valid,
                "reason": validation.strip(),
                "output": output
            }
            self.producer.send("validations", payload)
            self.producer.flush()
            self.validated_tasks.append(payload)

    def stop(self) -> None:
        """Stops the agent and closes the consumer."""
        self._running = False
        self.consumer.close()
        self.producer.close()


# ==============================================================================
# 5. Parallel Pipeline Orchestrator
# ==============================================================================

class StreamPipeline:
    """
    Orchestrates parallel background agent threads connected via Kafka streams.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        broker: Optional[InMemoryKafkaBroker] = None,
        bootstrap_servers: Optional[List[str]] = None
    ):
        self.broker = broker or InMemoryKafkaBroker.get_instance()
        self.bootstrap_servers = bootstrap_servers or ["localhost:9092"]
        self.model = model

        # Instantiate agents
        self.supervisor = SupervisorAgent(model=model, broker=self.broker, bootstrap_servers=self.bootstrap_servers)
        self.coding_specialist = SpecialistAgent("coding", model=model, broker=self.broker, bootstrap_servers=self.bootstrap_servers)
        self.reasoning_specialist = SpecialistAgent("reasoning", model=model, broker=self.broker, bootstrap_servers=self.bootstrap_servers)
        self.validator = ValidatorAgent(model=model, broker=self.broker, bootstrap_servers=self.bootstrap_servers)

        # Producer for injection and consumer for validation inspection
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            broker=self.broker
        )
        self.validations_consumer = KafkaConsumer(
            "validations",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"pipeline_verifier_{int(time.time()*1000)}",
            broker=self.broker
        )

        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        """Starts all agents on daemon threads in parallel."""
        agents = [
            (self.supervisor, "supervisor-thread"),
            (self.coding_specialist, "coding-spec-thread"),
            (self.reasoning_specialist, "reasoning-spec-thread"),
            (self.validator, "validator-thread"),
        ]
        for agent, name in agents:
            t = threading.Thread(target=agent.run, name=name, daemon=True)
            t.start()
            self._threads.append(t)

        time.sleep(0.05)  # Brief settling time

    def send_task(self, task_id: str, task_input: str, partition: Optional[int] = None) -> None:
        """Publishes task into 'tasks' topic."""
        self.producer.send("tasks", {"id": task_id, "input": task_input}, partition=partition)
        self.producer.flush()

    def wait_for_validation(self, task_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Awaits validation result for specified task_id."""
        deadline = time.time() + timeout
        for record in self.validations_consumer:
            val = record.value
            if val.get("task_id") == task_id:
                return val
            if time.time() > deadline:
                break
        return None

    def stop(self) -> None:
        """Gracefully shuts down all agents and threads."""
        self.supervisor.stop()
        self.coding_specialist.stop()
        self.reasoning_specialist.stop()
        self.validator.stop()
        self.validations_consumer.close()
        self.producer.close()


def run_message_stream_pipeline(
    task_id: str = "fizzbuzz_1",
    task_input: str = "Solve FizzBuzz in Python",
    model: str = "gpt-4o",
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Executes the user-specified Message Stream Pipeline end-to-end.
    """
    pipeline = StreamPipeline(model=model)
    try:
        pipeline.start()
        pipeline.send_task(task_id, task_input)
        result = pipeline.wait_for_validation(task_id, timeout=timeout)
        stats = pipeline.broker.get_topic_stats()
        return {
            "task_id": task_id,
            "task_input": task_input,
            "validation": result,
            "topic_stats": stats,
            "success": bool(result and result.get("is_valid", False))
        }
    finally:
        pipeline.stop()


# ==============================================================================
# 6. AgentMesh BaseTopology Adapter (StreamTopology)
# ==============================================================================

class StreamTopology(BaseTopology):
    """
    AgentMesh Topology Adapter for Event-Driven Message Streams:
    - Agent 1: Supervisor (produces routing decisions)
    - Agents 2 .. N-1: Specialists (consume routing decisions, produce work)
    - Agent N: Validator (consumes results, produces validations)
    """

    @property
    def name(self) -> str:
        return "STREAM"

    @property
    def supervisor(self) -> AgentInfo:
        for a in self.agents:
            if a.is_central:
                return a
        return self.agents[0]

    @property
    def validator(self) -> AgentInfo:
        return self.agents[-1]

    @property
    def specialists(self) -> List[AgentInfo]:
        sup = self.supervisor
        val = self.validator
        return [a for a in self.agents if a.id != sup.id and a.id != val.id]

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False

        sup_id = self.supervisor.id
        val_id = self.validator.id

        # 1. Supervisor -> Specialist (via 'routing-decisions')
        if sender_id == sup_id and receiver_id != val_id:
            return True

        # 2. Specialist -> Validator (via 'specialist-results')
        if receiver_id == val_id and sender_id != sup_id:
            return True

        # 3. Validator -> Supervisor (via 'validations')
        if sender_id == val_id and receiver_id == sup_id:
            return True

        return False

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        sup_id = self.supervisor.id
        val_id = self.validator.id

        if sender_id == sup_id:
            return [a.id for a in self.specialists]
        elif sender_id == val_id:
            return [sup_id]
        else:
            return [val_id]

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        edges = []
        sup_id = self.supervisor.id
        val_id = self.validator.id

        for spec in self.specialists:
            edges.append((sup_id, spec.id))
            edges.append((spec.id, val_id))

        edges.append((val_id, sup_id))
        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Message Stream turn planning:
        - Phase 0: Supervisor routes to Specialist via 'routing-decisions'
        - Phase 1: Specialist submits results to Validator via 'specialist-results'
        - Phase 2: Validator returns verdict to Supervisor via 'validations'
        """
        sup = self.supervisor
        val = self.validator
        specs = self.specialists if self.specialists else [self.agents[1]]

        phase = turn_idx % 3
        spec_idx = (turn_idx // 3) % len(specs)

        if phase == 0:
            return [(sup, specs[spec_idx])]
        elif phase == 1:
            return [(specs[spec_idx], val)]
        else:
            return [(val, sup)]
