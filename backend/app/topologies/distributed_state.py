"""
Topology with Distributed State (etcd Coordination Pattern).

Architecture:
All agents share immutable state snapshots via a centralized coordination service (etcd pattern):

Time=0ms:
  Task submitted
  State v1: {task_id: "fizzbuzz", input: "Solve FizzBuzz"}
  Stored in: etcd["/execution/fizzbuzz/v1"]

Time=10ms:
  Supervisor reads: State v1
  Supervisor makes routing decision via LLM
  Supervisor writes: State v2: {v1, routing_decision: "coding"}
  Stored in: etcd["/execution/fizzbuzz/v2"]
  Publishes: "/events/fizzbuzz/state_updated" -> "2"

Time=20ms:
  Coding-Specialist reads: State v2
  Coding-Specialist processes work via LLM
  Coding-Specialist writes: State v3: {v2, specialist_output: [code]}
  Stored in: etcd["/execution/fizzbuzz/v3"]
  Publishes: "/events/fizzbuzz/state_updated" -> "3"

Time=30ms:
  Validator reads: State v3
  Validator verifies correctness via LLM
  Validator writes: State v4: {v3, validation_result: True}
  Stored in: etcd["/execution/fizzbuzz/v4"]
  Publishes: "/events/fizzbuzz/state_updated" -> "4"
"""

from __future__ import annotations

import collections
import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from app.topologies.actor_system import BaseLLMClient, get_llm_client
from app.topologies.base import AgentInfo, BaseTopology

logger = logging.getLogger(__name__)

# Try importing real etcd3 if installed
try:
    import etcd3 as real_etcd3
    HAS_REAL_ETCD3 = True
except ImportError:
    real_etcd3 = None
    HAS_REAL_ETCD3 = False


# ==============================================================================
# 1. Immutable Execution State Snapshot
# ==============================================================================

@dataclass
class ExecutionState:
    """
    Immutable execution state snapshot replicated in the distributed store.
    Each version transition represents a verified state increment (v1 -> v2 -> v3 -> v4).
    """
    version: int
    task_id: str
    input: str
    routing_decision: Optional[str] = None
    specialist_output: Optional[str] = None
    validation_result: Optional[bool] = None
    reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 2. In-Memory Distributed Coordination Store (etcd API Compatibility)
# ==============================================================================

@dataclass
class WatchEvent:
    """Replicates etcd3 PutEvent / DeleteEvent."""
    type: str  # 'PUT' or 'DELETE'
    key: bytes
    value: bytes


@dataclass
class WatchResponse:
    """Replicates etcd3 WatchResponse holding events."""
    events: List[WatchEvent]


class _WatchIterator:
    """Iterator returned by watch() yielding WatchResponse events."""

    def __init__(self, key: str, broker: InMemoryEtcdClient):
        self.key = key
        self.broker = broker
        self._queue: collections.deque[WatchResponse] = collections.deque()
        self._closed = False

    def push(self, response: WatchResponse) -> None:
        self._queue.append(response)

    def close(self) -> None:
        self._closed = True

    def __iter__(self) -> Iterator[WatchResponse]:
        return self

    def __next__(self) -> WatchResponse:
        deadline = time.time() + 60.0
        while not self._closed:
            with self.broker._lock:
                if self._queue:
                    return self._queue.popleft()
                if self.broker._is_shutdown:
                    break

            with self.broker._condition:
                if not self._queue and not self._closed and not self.broker._is_shutdown:
                    self.broker._condition.wait(timeout=0.1)

            if time.time() > deadline:
                break

        raise StopIteration


class InMemoryEtcdClient:
    """
    Thread-safe, linearizable in-memory key-value coordination store.
    Emulates the etcd3 client API:
    - get(key) -> (value_bytes, metadata)
    - put(key, value_bytes) -> None
    - watch(key) -> Iterator[WatchResponse]
    - get_prefix(prefix) -> List[Tuple[value_bytes, metadata]]
    """

    _instance: Optional[InMemoryEtcdClient] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> InMemoryEtcdClient:
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

    def __init__(self):
        self._store: Dict[str, bytes] = {}
        self._watchers: Dict[str, List[_WatchIterator]] = collections.defaultdict(list)
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._is_shutdown = False

    def get(self, key: str) -> Optional[Tuple[bytes, Any]]:
        """Reads value by key. Returns (bytes, metadata) or None if key not present."""
        with self._lock:
            if key in self._store:
                return (self._store[key], {"key": key, "version": len(self._store[key])})
            return None

    def put(self, key: str, value: Union[bytes, str]) -> None:
        """Stores value by key and dispatches PUT event to all active watchers."""
        val_bytes = value if isinstance(value, bytes) else str(value).encode("utf-8")
        key_bytes = key.encode("utf-8")

        with self._condition:
            if self._is_shutdown:
                raise RuntimeError("Coordination store is shut down.")

            self._store[key] = val_bytes

            # Notify watchers subscribed to this key
            event = WatchEvent(type="PUT", key=key_bytes, value=val_bytes)
            response = WatchResponse(events=[event])

            watchers = self._watchers.get(key, [])
            for w in watchers:
                w.push(response)

            self._condition.notify_all()

    def watch(self, key: str) -> _WatchIterator:
        """Registers a watch stream on a specific key."""
        with self._lock:
            it = _WatchIterator(key, self)
            # If key already exists in store, immediately pre-populate an initial event
            if key in self._store:
                init_event = WatchEvent(type="PUT", key=key.encode("utf-8"), value=self._store[key])
                it.push(WatchResponse(events=[init_event]))

            self._watchers[key].append(it)
            return it

    def get_prefix(self, prefix: str) -> List[Tuple[bytes, Any]]:
        """Returns all key-value entries matching prefix."""
        with self._lock:
            results = []
            for k, v in sorted(self._store.items()):
                if k.startswith(prefix):
                    results.append((v, {"key": k}))
            return results

    def shutdown(self) -> None:
        """Shuts down store and closes all active watch streams."""
        with self._condition:
            self._is_shutdown = True
            for it_list in self._watchers.values():
                for it in it_list:
                    it.close()
            self._condition.notify_all()


def get_etcd_client(
    host: str = "localhost",
    port: int = 2379,
    use_real: bool = False
) -> Any:
    """
    Factory creating an etcd client.
    If real etcd3 is available and use_real=True, connects to live etcd cluster.
    Otherwise, returns linearizable InMemoryEtcdClient.
    """
    if use_real and HAS_REAL_ETCD3 and real_etcd3 is not None:
        try:
            return real_etcd3.client(host=host, port=port, timeout=2)
        except Exception as err:
            logger.warning(f"Live etcd3 cluster unreachable ({err}), falling back to InMemoryEtcdClient.")
    return InMemoryEtcdClient.get_instance()


# ==============================================================================
# 3. Distributed Agents (State Coordination Pattern)
# ==============================================================================

class DistributedAgent:
    """
    Agent that reads and writes distributed immutable state snapshots
    to the shared coordination store.
    """

    def __init__(
        self,
        agent_name: str,
        model: str,
        etcd_client: Optional[Any] = None,
        host: str = "localhost",
        port: int = 2379,
        use_mock: Optional[bool] = None
    ):
        self.name = agent_name
        self.model = model
        self.llm_client: BaseLLMClient = get_llm_client(model, use_mock=use_mock)
        self.etcd = etcd_client or get_etcd_client(host=host, port=port)

    def get_state(self, task_id: str, version: int) -> Optional[ExecutionState]:
        """Read state snapshot from distributed store."""
        key = f"/execution/{task_id}/v{version}"
        value = self.etcd.get(key)
        if value and value[0]:
            raw_bytes = value[0]
            data = json.loads(raw_bytes.decode("utf-8") if isinstance(raw_bytes, (bytes, bytearray)) else raw_bytes)
            return ExecutionState(**data)
        return None

    def publish_state(self, task_id: str, state: ExecutionState) -> None:
        """Write immutable state snapshot to distributed store and emit event."""
        key = f"/execution/{task_id}/v{state.version}"
        value_bytes = json.dumps(state.to_dict()).encode("utf-8")
        self.etcd.put(key, value_bytes)

        # Notify watchers
        event_key = f"/events/{task_id}/state_updated"
        self.etcd.put(event_key, str(state.version).encode("utf-8"))

    def wait_for_state(self, task_id: str, version: int, timeout: float = 15.0) -> Dict[str, Any]:
        """Block until state version is published and available."""
        key = f"/execution/{task_id}/v{version}"

        # 1. Fast check if key is already present
        existing = self.etcd.get(key)
        if existing and existing[0]:
            val_bytes = existing[0]
            return json.loads(val_bytes.decode("utf-8") if isinstance(val_bytes, (bytes, bytearray)) else val_bytes)

        # 2. Watch for arrival
        deadline = time.time() + timeout
        watch_iter = self.etcd.watch(key)

        for watch_response in watch_iter:
            for event in watch_response.events:
                if event.type == "PUT":
                    val_bytes = event.value
                    return json.loads(val_bytes.decode("utf-8") if isinstance(val_bytes, (bytes, bytearray)) else val_bytes)
            if time.time() > deadline:
                break

        raise TimeoutError(f"State v{version} not ready for task '{task_id}' after {timeout}s.")


class SupervisorAgent(DistributedAgent):
    """
    Supervisor using distributed state:
    - Reads State v1 from /execution/{task_id}/v1
    - Makes routing decision via LLM
    - Publishes State v2 to /execution/{task_id}/v2
    - Awaits State v3 (from Specialist)
    - Validates candidate solution via LLM
    - Publishes State v4 to /execution/{task_id}/v4
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        etcd_client: Optional[Any] = None,
        use_mock: Optional[bool] = None
    ):
        super().__init__("supervisor", model, etcd_client, use_mock=use_mock)
        self.processed_tasks: List[str] = []

    def run(self, task_id: str, timeout: float = 10.0) -> ExecutionState:
        """Executes supervisor workflow transitioning v1 -> v2, and optionally v3 -> v4."""
        # 1. Read initial state v1
        state_v1 = self.get_state(task_id, version=1)
        if not state_v1:
            state_v1_dict = self.wait_for_state(task_id, version=1, timeout=timeout)
            state_v1 = ExecutionState(**state_v1_dict)

        # 2. Make routing decision
        decision = self.llm_client.call(
            system="Route this task. Return 'coding' or 'reasoning'.",
            user=state_v1.input
        )
        clean_decision = "coding" if "coding" in decision.lower() else "reasoning"

        # 3. Publish State v2
        state_v2 = ExecutionState(
            version=2,
            task_id=task_id,
            input=state_v1.input,
            routing_decision=clean_decision
        )
        self.publish_state(task_id, state_v2)
        self.processed_tasks.append(task_id)
        return state_v2

    def validate_and_finalize(self, task_id: str, timeout: float = 10.0) -> ExecutionState:
        """Awaits State v3 from Specialist and writes final State v4."""
        # Await specialist result (State v3)
        state_v3_dict = self.wait_for_state(task_id, version=3, timeout=timeout)

        # Evaluate correctness
        output = state_v3_dict.get("specialist_output", "")
        validation = self.llm_client.call(
            system="Validate output. Does it satisfy all constraints? Reply 'YES' or 'NO' followed by diagnostic reasoning.",
            user=output
        )
        is_valid = "yes" in validation.lower()

        state_v4 = ExecutionState(
            version=4,
            task_id=task_id,
            input=state_v3_dict.get("input", ""),
            routing_decision=state_v3_dict.get("routing_decision"),
            specialist_output=output,
            validation_result=is_valid,
            reason=validation.strip()
        )
        self.publish_state(task_id, state_v4)
        return state_v4


class SpecialistAgent(DistributedAgent):
    """
    Specialist using distributed state:
    - Waits for State v2 (/execution/{task_id}/v2)
    - Filters: only processes if routing_decision == self.type
    - Invokes domain-specialized LLM prompt
    - Publishes State v3 to /execution/{task_id}/v3
    """

    def __init__(
        self,
        spec_type: str,
        model: str = "gpt-4o",
        etcd_client: Optional[Any] = None,
        use_mock: Optional[bool] = None
    ):
        super().__init__(f"specialist_{spec_type}", model, etcd_client, use_mock=use_mock)
        self.type = spec_type
        self.completed_tasks: List[str] = []

    def run(self, task_id: str, timeout: float = 10.0) -> Optional[ExecutionState]:
        """Awaits State v2, filters, and generates State v3."""
        # Wait for routing decision (State v2)
        state_v2_dict = self.wait_for_state(task_id, version=2, timeout=timeout)

        # Filter: only process if routed to this specialist
        if state_v2_dict.get("routing_decision") != self.type:
            return None

        # Do work
        output = self.llm_client.call(
            system=f"You are a {self.type} specialist. Provide a detailed, robust, and logically sound solution.",
            user=state_v2_dict.get("input", "")
        )

        # Update and publish State v3
        state_v3 = ExecutionState(
            version=3,
            task_id=task_id,
            input=state_v2_dict.get("input", ""),
            routing_decision=state_v2_dict.get("routing_decision"),
            specialist_output=output
        )
        self.publish_state(task_id, state_v3)
        self.completed_tasks.append(task_id)
        return state_v3


class ValidatorAgent(DistributedAgent):
    """
    Dedicated Validator using distributed state:
    - Waits for State v3 (/execution/{task_id}/v3)
    - Audits output against acceptance criteria
    - Publishes State v4 to /execution/{task_id}/v4
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        criteria: Optional[str] = None,
        etcd_client: Optional[Any] = None,
        use_mock: Optional[bool] = None
    ):
        super().__init__("validator", model, etcd_client, use_mock=use_mock)
        self.criteria = criteria or "Correctness, constraint adherence, completeness, and logical consistency."
        self.validation_history: List[ExecutionState] = []

    def run(self, task_id: str, timeout: float = 10.0) -> ExecutionState:
        """Awaits State v3 and publishes validated State v4."""
        state_v3_dict = self.wait_for_state(task_id, version=3, timeout=timeout)
        output = state_v3_dict.get("specialist_output", "")

        validation = self.llm_client.call(
            system=(
                f"You are the Solution Validator. Evaluate whether the proposed output satisfies "
                f"the criteria: '{self.criteria}'. Reply with 'YES' or 'NO' followed by a concise diagnostic justification."
            ),
            user=output
        )
        is_valid = "yes" in validation.lower()

        state_v4 = ExecutionState(
            version=4,
            task_id=task_id,
            input=state_v3_dict.get("input", ""),
            routing_decision=state_v3_dict.get("routing_decision"),
            specialist_output=output,
            validation_result=is_valid,
            reason=validation.strip()
        )
        self.publish_state(task_id, state_v4)
        self.validation_history.append(state_v4)
        return state_v4


# ==============================================================================
# 4. Pipeline Runner
# ==============================================================================

def run_distributed_state_pipeline(
    task_id: str = "fizzbuzz",
    task_input: str = "Solve FizzBuzz in Python from 1 to 15",
    model: str = "gpt-4o",
    timeout: float = 5.0,
    etcd_client: Optional[Any] = None,
    use_mock: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end Distributed State workflow across parallel worker threads.
    Timeline:
    - Time=0ms: State v1 submitted to etcd
    - Time=10ms: SupervisorAgent routes -> writes State v2
    - Time=20ms: SpecialistAgent processes -> writes State v3
    - Time=30ms: ValidatorAgent verifies -> writes State v4
    """
    etcd = etcd_client or InMemoryEtcdClient.get_instance()

    # Time=0ms: Publish initial state v1
    state_v1 = ExecutionState(version=1, task_id=task_id, input=task_input)
    key_v1 = f"/execution/{task_id}/v1"
    etcd.put(key_v1, json.dumps(state_v1.to_dict()).encode("utf-8"))

    # Instantiate agents
    supervisor = SupervisorAgent(model=model, etcd_client=etcd, use_mock=use_mock)
    coding_spec = SpecialistAgent("coding", model=model, etcd_client=etcd, use_mock=use_mock)
    reasoning_spec = SpecialistAgent("reasoning", model=model, etcd_client=etcd, use_mock=use_mock)
    validator = ValidatorAgent(model=model, etcd_client=etcd, use_mock=use_mock)

    threads = [
        threading.Thread(target=supervisor.run, args=(task_id,), daemon=True),
        threading.Thread(target=coding_spec.run, args=(task_id,), daemon=True),
        threading.Thread(target=reasoning_spec.run, args=(task_id,), daemon=True),
        threading.Thread(target=validator.run, args=(task_id,), daemon=True),
    ]

    for t in threads:
        t.start()

    # Wait for final state v4
    try:
        final_v4_dict = supervisor.wait_for_state(task_id, version=4, timeout=timeout)
        final_state = ExecutionState(**final_v4_dict)
    except TimeoutError:
        final_state = None

    # Retrieve all versions for this execution
    prefix = f"/execution/{task_id}/"
    entries = etcd.get_prefix(prefix)
    history = {}
    for raw_val, meta in entries:
        d = json.loads(raw_val.decode("utf-8") if isinstance(raw_val, (bytes, bytearray)) else raw_val)
        history[f"v{d.get('version')}"] = d

    return {
        "task_id": task_id,
        "task_input": task_input,
        "final_state": final_state.to_dict() if final_state else None,
        "history": history,
        "success": bool(final_state and final_state.validation_result)
    }


# ==============================================================================
# 5. AgentMesh BaseTopology Adapter (DistributedStateTopology)
# ==============================================================================

class DistributedStateTopology(BaseTopology):
    """
    AgentMesh Topology Adapter for Topology with Distributed State:
    - Agent 1: Supervisor (reads State v1, writes State v2)
    - Agents 2 .. N-1: Specialists (reads State v2, writes State v3)
    - Agent N: Validator (reads State v3, writes State v4)
    """

    @property
    def name(self) -> str:
        return "DISTRIBUTED_STATE"

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

        # 1. Supervisor -> Specialist (State v1 -> State v2)
        if sender_id == sup_id and receiver_id != val_id:
            return True

        # 2. Specialist -> Validator (State v2 -> State v3)
        if receiver_id == val_id and sender_id != sup_id:
            return True

        # 3. Validator -> Supervisor (State v3 -> State v4)
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
        Distributed State turn planning matching version transitions:
        - Turn 0: Supervisor publishes State v2 -> Specialist perceives v2
        - Turn 1: Specialist publishes State v3 -> Validator perceives v3
        - Turn 2: Validator publishes State v4 -> Supervisor perceives v4
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
