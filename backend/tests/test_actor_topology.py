import pytest
import dataclasses
from app.topologies.actor_system import (
    Actor,
    Message,
    TaskRequest,
    RouteMessage,
    ResultMessage,
    FinalResult,
    Mailbox,
    SupervisorActor,
    SpecialistActor,
    ValidatorActor,
    ActorSystem,
    get_llm_client,
    run_distributed_topology
)
from app.topologies.actor import ActorTopology
from app.topologies import get_topology_instance
from app.services.agent_service import create_agent_team


def test_message_immutability():
    """Verify that Message objects are strictly immutable (frozen)."""
    msg = Message(sender_id="sup", receiver_id="spec", content={"test": 123}, timestamp=100.0)
    assert msg.sender_id == "sup"
    assert msg.receiver_id == "spec"
    assert msg.content["test"] == 123

    # Mutating frozen dataclass attribute should raise FrozenInstanceError
    with pytest.raises(dataclasses.FrozenInstanceError):
        msg.sender_id = "new_sender"


def test_typed_message_constructors():
    """Verify TaskRequest, RouteMessage, ResultMessage, and FinalResult typed behaviors."""
    req = TaskRequest(task_id="t1", task_input="Calculate 2 + 2")
    assert req.task_id == "t1"
    assert req.task_input == "Calculate 2 + 2"
    assert req.receiver_id == "supervisor"

    route = RouteMessage(task_id="t1", specialist_type="math", data="2 + 2")
    assert route.task_id == "t1"
    assert route.specialist_type == "math"
    assert route.receiver_id == "specialist_math"

    res = ResultMessage(task_id="t1", specialist_type="math", output="4")
    assert res.task_id == "t1"
    assert res.output == "4"
    assert res.sender_id == "specialist_math"

    final = FinalResult(task_id="t1", output="4", is_valid=True, reason="Verified correct")
    assert final.is_valid is True
    assert final.output == "4"
    assert final.reason == "Verified correct"


@pytest.mark.asyncio
async def test_mailbox_queue_operations():
    """Verify async FIFO queuing, stats, and history on Mailbox."""
    mbox = Mailbox(owner_id="test_actor", capacity=50)
    assert mbox.is_empty() is True
    assert mbox.size == 0

    m1 = Message(sender_id="a", receiver_id="test_actor", content={"seq": 1})
    m2 = Message(sender_id="b", receiver_id="test_actor", content={"seq": 2})

    mbox.put_nowait(m1)
    await mbox.put(m2)

    assert mbox.size == 2
    assert mbox.is_empty() is False

    rec1 = await mbox.get()
    assert rec1.content["seq"] == 1

    rec2 = await mbox.get()
    assert rec2.content["seq"] == 2

    assert mbox.is_empty() is True
    stats = mbox.stats()
    assert stats["total_received"] == 2
    assert stats["total_processed"] == 2


def test_supervisor_actor_routing_and_validation():
    """Verify SupervisorActor routing logic and result validation."""
    sup = SupervisorActor(model="gpt-4o")

    # Coding task
    route_code = sup.process_task("t_code", "Write a python function to reverse a string")
    assert "coding" in route_code.receiver_id
    assert route_code.content["task_id"] == "t_code"

    # Math task
    route_math = sup.process_task("t_math", "Solve differential equation y' + y = 0")
    assert "math" in route_math.receiver_id

    # Validation check
    val_yes = sup.validate_result("def reverse(s): return s[::-1]")
    assert val_yes is True

    val_no = sup.validate_result("SyntaxError: invalid syntax")
    assert val_no is False


def test_specialist_actor_processing():
    """Verify SpecialistActor processes work requests and emits ResultMessages."""
    coding_spec = SpecialistActor("coding", model="gpt-4o")
    reasoning_spec = SpecialistActor("reasoning", model="gpt-4o")

    work_msg = Message(
        sender_id="supervisor",
        receiver_id="specialist_coding",
        content={"task_id": "job_1", "data": "Solve fizzbuzz up to 15"}
    )

    res = coding_spec.process_work(work_msg)
    assert res.sender_id == "specialist_coding"
    assert res.receiver_id == "supervisor"
    assert "python" in res.content["output"].lower() or "fizzbuzz" in res.content["output"].lower()
    assert coding_spec.completed_jobs == 1

    res_reason = reasoning_spec.process_work(
        Message(sender_id="sup", receiver_id="reason", content={"task_id": "job_2", "data": "Analyze premise"})
    )
    assert res_reason.sender_id == "specialist_reasoning"
    assert len(res_reason.content["output"]) > 20


def test_validator_actor_evaluation():
    """Verify ValidatorActor evaluates output and returns FinalResult."""
    validator = ValidatorActor(model="gpt-4o", criteria="Accurate implementation")

    valid_work = Message(
        sender_id="specialist_coding",
        receiver_id="validator",
        content={"task_id": "job_1", "output": "def add(a, b): return a + b"}
    )

    final_res = validator.validate_output(valid_work)
    assert isinstance(final_res, FinalResult)
    assert final_res.is_valid is True
    assert len(final_res.reason) > 0


@pytest.mark.asyncio
async def test_actor_system_dispatch():
    """Verify ActorSystem routing between actors with mailboxes."""
    system = ActorSystem("TestSystem")
    sup = SupervisorActor()
    spec = SpecialistActor("coding")
    spec_reason = SpecialistActor("reasoning")
    val = ValidatorActor()

    system.register_actor("supervisor", sup)
    system.register_actor("specialist_coding", spec)
    system.register_actor("specialist_reasoning", spec_reason)
    system.register_actor("validator", val)

    req = TaskRequest(task_id="system_t1", task_input="Write python function")
    await system.send_message(req)

    # Check supervisor mailbox
    sup_msg = await sup.mailbox.get()
    assert sup_msg.content["task_id"] == "system_t1"

    # Supervisor routes
    route_msg = sup.process_task(sup_msg.content["task_id"], sup_msg.content["data"])
    await system.send_message(route_msg)

    # Identify which specialist received it
    active_spec = spec if route_msg.receiver_id == "specialist_coding" else spec_reason
    spec_msg = await active_spec.mailbox.get()
    assert spec_msg.content["task_id"] == "system_t1"

    # Specialist processes
    res = active_spec.process_work(spec_msg)
    # Forward work result to validator
    val_submission = Message(sender_id=res.sender_id, receiver_id="validator", content=res.content)
    await system.send_message(val_submission)

    # Validator receives
    val_msg = await val.mailbox.get()
    final = val.validate_output(val_msg)
    assert final.is_valid is True
    assert len(system.message_trace) == 3


@pytest.mark.asyncio
async def test_run_distributed_topology():
    """Verify end-to-end distributed topology execution using the .remote() interface."""
    summary = await run_distributed_topology(
        task_id="fizzbuzz",
        task_input="Solve FizzBuzz in Python",
        model="gpt-4o"
    )

    assert summary["task_id"] == "fizzbuzz"
    assert "route_message" in summary
    assert "result_message" in summary
    assert summary["is_valid"] is True
    assert isinstance(summary["final_result"], FinalResult)
    assert len(summary["output"]) > 10


def test_actor_topology_integration_in_agentmesh():
    """Verify ActorTopology permissions and turn planning integrated in AgentMesh."""
    agents = create_agent_team(num_agents=5)
    actor_topo = ActorTopology(agents)

    assert actor_topo.name == "ACTOR"
    supervisor_id = agents[0].id
    spec_1_id = agents[1].id
    spec_2_id = agents[2].id
    validator_id = agents[-1].id

    # Allowed: Supervisor <-> Specialist
    assert actor_topo.is_allowed_communication(supervisor_id, spec_1_id) is True
    assert actor_topo.is_allowed_communication(spec_1_id, supervisor_id) is True

    # Allowed: Specialist -> Validator
    assert actor_topo.is_allowed_communication(spec_1_id, validator_id) is True

    # Allowed: Validator -> Supervisor
    assert actor_topo.is_allowed_communication(validator_id, supervisor_id) is True

    # Disallowed: Lateral Specialist <-> Specialist
    assert actor_topo.is_allowed_communication(spec_1_id, spec_2_id) is False
    assert actor_topo.is_allowed_communication(spec_2_id, spec_1_id) is False

    # Turn planning phases
    plan_t0 = actor_topo.plan_turn(0, [])
    assert plan_t0[0][0].id == supervisor_id  # Supervisor sends

    plan_t1 = actor_topo.plan_turn(1, [])
    assert plan_t1[0][1].id == supervisor_id  # Specialist responds to supervisor

    plan_t2 = actor_topo.plan_turn(2, [])
    assert plan_t2[0][0].id == validator_id  # Validator responds to supervisor

    # Registered in factory
    inst = get_topology_instance("ACTOR", agents)
    assert inst.name == "ACTOR"


@pytest.mark.asyncio
async def test_actor_base_tell_ask_and_supervision():
    """Verify Actor tell, ask request-reply, and ActorSystem error supervision."""
    system = ActorSystem("SupervisedSystem")
    sup = SupervisorActor()
    spec = SpecialistActor("coding")

    system.register_actor("supervisor", sup)
    system.register_actor("specialist_coding", spec)

    # 1. Test ask() pattern: request-reply
    route_reply = await system.ask(
        TaskRequest(task_id="ask_t1", task_input="Write python function", receiver_id="supervisor"),
        timeout=2.0
    )
    assert isinstance(route_reply, (Message, RouteMessage))
    assert route_reply.receiver_id == "specialist_coding"

    # 2. Test tell() pattern on actor instance
    await spec.tell(route_reply)
    queued_msg = await spec.mailbox.get()
    assert queued_msg.content["task_id"] == "ask_t1"

    # 3. Test supervision strategy
    action_val = system.supervise("supervisor", ValueError("Invalid argument"))
    assert action_val == "restart"

    action_timeout = system.supervise("supervisor", TimeoutError("Timed out"))
    assert action_timeout == "resume"

    action_esc = system.supervise("supervisor", RuntimeError("Fatal hardware crash"))
    assert action_esc == "escalate"

    log = system.get_supervision_log()
    assert len(log) == 3
    assert log[0]["error_type"] == "ValueError"

