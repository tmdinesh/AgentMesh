"""
Interactive Benchmark & Demonstration for the Actor Topology System.
Runs both Ray-compatible distributed actor workflow and in-process mailbox-based ActorSystem.
"""

import asyncio
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.topologies.actor_system import (
    Actor,
    Message,
    TaskRequest,
    RouteMessage,
    ResultMessage,
    FinalResult,
    SupervisorActor,
    SpecialistActor,
    ValidatorActor,
    ActorSystem,
    run_distributed_topology,
    HAS_RAY,
    ray_init,
    ray_shutdown
)


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def demo_ray_distributed_topology():
    print_banner("1. RAY-COMPATIBLE DISTRIBUTED ACTOR TOPOLOGY (.remote)")
    print(f"[*] Ray Installed: {HAS_RAY}")
    print("[*] Initializing Distributed Actor Topology...")

    task_id = "task_fizzbuzz_001"
    task_input = "Implement FizzBuzz in Python from 1 to 15 with comments and complexity analysis."
    model = "gpt-4o"

    print(f"[*] Task ID: {task_id}")
    print(f"[*] Task Input: {task_input}\n")

    # Start Ray environment
    ray_init()

    try:
        # Instantiate remote actors
        print("[+] Instantiating Actors:")
        supervisor = SupervisorActor.remote(model=model)
        coding_specialist = SpecialistActor.remote("coding", model=model)
        reasoning_specialist = SpecialistActor.remote("reasoning", model=model)
        validator = ValidatorActor.remote(model=model, criteria="Clean code, correct logic, O(N) complexity")

        print("    - SupervisorActor.remote(...) [Mailbox: requests]")
        print("    - SpecialistActor.remote('coding') [Mailbox: work requests]")
        print("    - SpecialistActor.remote('reasoning') [Mailbox: work requests]")
        print("    - ValidatorActor.remote(...) [Mailbox: results]")

        # Phase 1: Supervisor routes
        print("\n--- PHASE 1: Supervisor Routes Task ---")
        route_msg: Message = await supervisor.process_task.remote(task_id, task_input)
        print(f"[*] Supervisor Decision -> Receiver: {route_msg.receiver_id}")
        print(f"[*] RouteMessage Content: {route_msg.content}")

        # Phase 2: Parallel Specialist Execution
        print("\n--- PHASE 2: Specialist Processes Work (Concurrent Mailbox Delivery) ---")
        # In this scenario, we can invoke the routed specialist or run both in parallel
        if "coding" in route_msg.receiver_id:
            target_specialist = coding_specialist
        else:
            target_specialist = reasoning_specialist

        # Execute specialist
        result_msg: Message = await target_specialist.process_work.remote(route_msg)
        print(f"[*] Specialist Response Received From: {result_msg.sender_id}")
        print(f"[*] Specialist Output Preview:\n{result_msg.content['output'][:220]}...\n")

        # Phase 3: Supervisor validation & ValidatorActor Audit
        print("--- PHASE 3: Validation and Verification ---")
        supervisor_verdict = await supervisor.validate_result.remote(result_msg.content["output"])
        print(f"[*] Supervisor Simple Check: {'PASSED (yes)' if supervisor_verdict else 'FAILED'}")

        # ValidatorActor in-depth audit
        final_result: FinalResult = await validator.validate_output.remote(result_msg)
        print(f"[*] ValidatorActor Outcome: {'VALIDATED' if final_result.is_valid else 'REJECTED'}")
        print(f"[*] Validator Diagnostic Reason:\n    {final_result.reason}")

    finally:
        ray_shutdown()


async def demo_mailbox_actor_system():
    print_banner("2. IN-PROCESS ACTOR SYSTEM WITH ASYNC MAILBOXES (Akka Pattern)")
    
    system = ActorSystem(name="MeshActorCluster")
    print(f"[*] Initialized ActorSystem: {system.name}")

    # Create concrete actors
    sup = SupervisorActor(model="gpt-4o")
    coding_spec = SpecialistActor("coding", model="gpt-4o")
    reasoning_spec = SpecialistActor("reasoning", model="gpt-4o")
    val = ValidatorActor(model="gpt-4o")

    # Register into system
    system.register_actor("supervisor", sup)
    system.register_actor("specialist_coding", coding_spec)
    system.register_actor("specialist_reasoning", reasoning_spec)
    system.register_actor("validator", val)

    print("[+] Actors registered with isolated Mailboxes:")
    for a_id in ["supervisor", "specialist_coding", "specialist_reasoning", "validator"]:
        mbox = system.get_mailbox(a_id)
        print(f"    - {a_id}: Mailbox owner={mbox.owner_id}, capacity={mbox.capacity}, current_size={mbox.size}")

    # Send client task request
    task_req = TaskRequest(
        task_id="task_logic_002",
        task_input="A farmer needs to cross a river with a fox, goose, and bag of beans. How can he cross safely?"
    )

    print("\n[+] Client sends TaskRequest to Supervisor mailbox:")
    await system.send_message(task_req)
    print(f"    Supervisor Mailbox size: {sup.mailbox.size}")

    # Supervisor processes
    pending_task = await sup.mailbox.get()
    route_msg = sup.process_task(pending_task.task_id, pending_task.task_input)
    print(f"[+] Supervisor processed request -> Routed to: {route_msg.receiver_id}")

    # Deliver RouteMessage via ActorSystem
    await system.send_message(route_msg)
    target_actor = system.actors.get(route_msg.receiver_id)
    print(f"    Target Mailbox ({route_msg.receiver_id}) size: {target_actor.mailbox.size}")

    # Specialist picks up work from its mailbox
    work_msg = await target_actor.mailbox.get()
    res_msg = target_actor.process_work(work_msg)
    print(f"[+] Specialist completed work. Output snippet: {res_msg.output[:120]}...")

    # Forward to Validator mailbox
    val_submission = ResultMessage(
        task_id=res_msg.task_id,
        specialist_type=res_msg.specialist_type,
        output=res_msg.output,
        sender_id=res_msg.sender_id,
        receiver_id="validator"
    )
    await system.tell(val_submission)
    val_inbox_msg = await val.mailbox.get()
    final_res = val.validate_output(val_inbox_msg)

    print(f"[+] Validator emitted FinalResult: is_valid={final_res.is_valid}")
    print(f"    Reason: {final_res.reason}")

    print("\n[+] Actor System Telemetry & Statistics:")
    for a_id, mbox in system.mailboxes.items():
        print(f"    {a_id}: {mbox.stats()}")


async def main():
    print_banner("MAST TOPOLOGY LAB - ACTOR TOPOLOGY BENCHMARK SUITE")
    await demo_ray_distributed_topology()
    await demo_mailbox_actor_system()
    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
