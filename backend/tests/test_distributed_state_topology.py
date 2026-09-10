import json
import time
import threading
import pytest

from app.topologies.distributed_state import (
    ExecutionState,
    InMemoryEtcdClient,
    SupervisorAgent,
    SpecialistAgent,
    ValidatorAgent,
    DistributedStateTopology,
    run_distributed_state_pipeline
)
from app.topologies import get_topology_instance
from app.services.agent_service import create_agent_team


@pytest.fixture(autouse=True)
def reset_etcd():
    """Ensure clean etcd client state per test."""
    InMemoryEtcdClient.reset_instance()
    yield
    InMemoryEtcdClient.reset_instance()


def test_execution_state_serialization():
    """Verify ExecutionState dataclass properties and serialization."""
    st = ExecutionState(
        version=1,
        task_id="task_001",
        input="Write Python function",
        routing_decision="coding"
    )
    d = st.to_dict()
    assert d["version"] == 1
    assert d["task_id"] == "task_001"
    assert d["routing_decision"] == "coding"

    # Reconstruct
    st2 = ExecutionState(**d)
    assert st2.version == 1
    assert st2.input == "Write Python function"


def test_in_memory_etcd_get_put_prefix():
    """Verify InMemoryEtcdClient stores values and matches prefixes."""
    etcd = InMemoryEtcdClient()
    etcd.put("/execution/task_a/v1", b"state_v1")
    etcd.put("/execution/task_a/v2", b"state_v2")
    etcd.put("/execution/task_b/v1", b"state_b_v1")

    # Get single key
    val, meta = etcd.get("/execution/task_a/v1")
    assert val == b"state_v1"

    # Prefix query
    entries = etcd.get_prefix("/execution/task_a/")
    assert len(entries) == 2
    assert entries[0][0] == b"state_v1"
    assert entries[1][0] == b"state_v2"


def test_in_memory_etcd_watch():
    """Verify watch stream yields PUT event upon write."""
    etcd = InMemoryEtcdClient()
    key = "/execution/watch_test/v1"

    watch_iter = etcd.watch(key)

    def writer():
        time.sleep(0.05)
        etcd.put(key, b"hello_watcher")

    t = threading.Thread(target=writer)
    t.start()

    # Next watch response should catch the PUT event
    response = next(watch_iter)
    assert len(response.events) >= 1
    assert response.events[0].type == "PUT"
    assert response.events[0].value == b"hello_watcher"
    t.join()


def test_supervisor_reads_v1_and_writes_v2():
    """Verify SupervisorAgent reads State v1 and writes State v2."""
    etcd = InMemoryEtcdClient()
    task_id = "test_sup_t1"

    # Write initial state v1
    v1 = ExecutionState(version=1, task_id=task_id, input="Write a python algorithm")
    etcd.put(f"/execution/{task_id}/v1", json.dumps(v1.to_dict()).encode("utf-8"))

    supervisor = SupervisorAgent(model="gpt-4o", etcd_client=etcd, use_mock=True)
    state_v2 = supervisor.run(task_id)

    assert state_v2.version == 2
    assert state_v2.routing_decision == "coding"

    # Check store directly
    raw_v2 = etcd.get(f"/execution/{task_id}/v2")
    assert raw_v2 is not None
    data = json.loads(raw_v2[0].decode("utf-8"))
    assert data["routing_decision"] == "coding"


def test_specialist_agent_filters_and_processes():
    """Verify SpecialistAgent only acts if routing_decision matches."""
    etcd = InMemoryEtcdClient()
    task_id = "test_spec_t1"

    coding_spec = SpecialistAgent("coding", model="gpt-4o", etcd_client=etcd, use_mock=True)
    reasoning_spec = SpecialistAgent("reasoning", model="gpt-4o", etcd_client=etcd, use_mock=True)

    # Publish state v2 routed to coding
    v2 = ExecutionState(version=2, task_id=task_id, input="Solve FizzBuzz in Python", routing_decision="coding")
    etcd.put(f"/execution/{task_id}/v2", json.dumps(v2.to_dict()).encode("utf-8"))

    # Reasoning specialist should ignore (return None)
    res_reason = reasoning_spec.run(task_id, timeout=0.1)
    assert res_reason is None

    # Coding specialist should process and publish v3
    res_code = coding_spec.run(task_id, timeout=0.5)
    assert res_code is not None
    assert res_code.version == 3
    assert "python" in res_code.specialist_output.lower() or "fizzbuzz" in res_code.specialist_output.lower()

    # Verify stored in etcd
    raw_v3 = etcd.get(f"/execution/{task_id}/v3")
    assert raw_v3 is not None


def test_validator_agent_writes_v4():
    """Verify ValidatorAgent reads v3 and writes State v4 with success verdict."""
    etcd = InMemoryEtcdClient()
    task_id = "test_val_t1"

    validator = ValidatorAgent(model="gpt-4o", etcd_client=etcd, use_mock=True)

    # Put state v3
    v3 = ExecutionState(
        version=3,
        task_id=task_id,
        input="Write add function",
        routing_decision="coding",
        specialist_output="def add(a, b):\n    return a + b\n# Well-tested"
    )
    etcd.put(f"/execution/{task_id}/v3", json.dumps(v3.to_dict()).encode("utf-8"))

    state_v4 = validator.run(task_id, timeout=0.5)
    assert state_v4.version == 4
    assert state_v4.validation_result is True
    assert len(state_v4.reason) > 0

    raw_v4 = etcd.get(f"/execution/{task_id}/v4")
    assert raw_v4 is not None


def test_run_distributed_state_pipeline_end_to_end():
    """Verify complete multi-threaded pipeline from v1 to v4."""
    result = run_distributed_state_pipeline(
        task_id="fizzbuzz_e2e",
        task_input="Implement FizzBuzz in Python",
        model="gpt-4o",
        timeout=3.0,
        use_mock=True
    )

    assert result["success"] is True
    assert result["task_id"] == "fizzbuzz_e2e"
    assert result["final_state"] is not None
    assert result["final_state"]["version"] == 4
    assert result["final_state"]["validation_result"] is True

    history = result["history"]
    assert "v1" in history
    assert "v2" in history
    assert "v3" in history
    assert "v4" in history
    assert history["v2"]["routing_decision"] == "coding"


def test_distributed_state_topology_agentmesh_adapter():
    """Verify AgentMesh DistributedStateTopology permissions and turn phases."""
    agents = create_agent_team(num_agents=5)
    topo: DistributedStateTopology = get_topology_instance("DISTRIBUTED_STATE", agents)

    assert topo.name == "DISTRIBUTED_STATE"
    sup = topo.supervisor
    val = topo.validator
    specs = topo.specialists

    # Graph edges
    edges = topo.get_graph_edges()
    for spec in specs:
        assert (sup.id, spec.id) in edges
        assert (spec.id, val.id) in edges
    assert (val.id, sup.id) in edges

    # Permissions
    for spec in specs:
        assert topo.is_allowed_communication(sup.id, spec.id) is True
        assert topo.is_allowed_communication(spec.id, val.id) is True
        assert topo.is_allowed_communication(spec.id, sup.id) is False

    # Lateral specialists disallowed
    if len(specs) >= 2:
        assert topo.is_allowed_communication(specs[0].id, specs[1].id) is False

    # Turn plan phases
    t0 = topo.plan_turn(0, [])
    assert t0[0][0].id == sup.id
    assert t0[0][1].id in [s.id for s in specs]

    t1 = topo.plan_turn(1, [])
    assert t1[0][0].id in [s.id for s in specs]
    assert t1[0][1].id == val.id

    t2 = topo.plan_turn(2, [])
    assert t2[0][0].id == val.id
    assert t2[0][1].id == sup.id
