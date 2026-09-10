"""
Benchmark & Demonstration for Topology with Distributed State (etcd Coordination Pattern).

Architecture:
All agents share immutable state snapshots via coordination service (etcd pattern):

Time=0ms:
  Task submitted
  State v1: {task_id: "fizzbuzz", input: "Solve FizzBuzz"}
  Stored in: etcd["/execution/fizzbuzz/v1"]

Time=10ms:
  Supervisor reads: State v1
  Supervisor makes decision
  Supervisor writes: State v2: {v1, routing_decision: "coding"}
  Stored in: etcd["/execution/fizzbuzz/v2"]

Time=20ms:
  Coding-Specialist reads: State v2
  Coding-Specialist processes
  Coding-Specialist writes: State v3: {v2, output: [code]}
  Stored in: etcd["/execution/fizzbuzz/v3"]

Time=30ms:
  Validator reads: State v3
  Validator validates
  Validator writes: State v4: {v3, success: True}
  Stored in: etcd["/execution/fizzbuzz/v4"]
"""

import json
import os
import sys
import threading
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend and root are on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.topologies.distributed_state import (
    ExecutionState,
    InMemoryEtcdClient,
    SupervisorAgent,
    SpecialistAgent,
    ValidatorAgent,
    HAS_REAL_ETCD3
)


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_distributed_state_demo():
    print_banner("AGENTMESH: TOPOLOGY WITH DISTRIBUTED STATE (ETCD PATTERN)")
    print(f"[*] Real etcd3 Client Available: {HAS_REAL_ETCD3}")
    print("[*] Coordination Store: Linearizable In-Memory etcd Store (Dual-Mode)")
    print("""
+------------------------------------------------------------------------+
| Distributed State Architecture (Linearizable Key-Value Store)          |
+------------------------------------------------------------------------+
|  Time=0ms  | State v1 stored in:  /execution/{task_id}/v1               |
|  Time=10ms | Supervisor reads v1 -> writes State v2 (routing_decision) |
|  Time=20ms | Specialist reads v2 -> writes State v3 (output: [code])   |
|  Time=30ms | Validator reads v3  -> writes State v4 (success: True)     |
+------------------------------------------------------------------------+
""")

    etcd = InMemoryEtcdClient.get_instance()
    task_id = "fizzbuzz_distributed_001"
    task_input = "Solve FizzBuzz in Python from 1 to 15 with comments"
    model = "gpt-4o"

    print(f"[+] Task Configuration:")
    print(f"    Task ID:    {task_id}")
    print(f"    Task Input: {task_input}\n")

    # Instantiate Agents
    supervisor = SupervisorAgent(model=model, etcd_client=etcd)
    coding_spec = SpecialistAgent("coding", model=model, etcd_client=etcd)
    reasoning_spec = SpecialistAgent("reasoning", model=model, etcd_client=etcd)
    validator = ValidatorAgent(model=model, criteria="Clean code, correct logic, O(N) complexity", etcd_client=etcd)

    print("[+] Agents Connected to Coordination Store (etcd):")
    print("    * SupervisorAgent          [Watches: /execution/{task}/v1]")
    print("    * SpecialistAgent(coding)  [Watches: /execution/{task}/v2 | Filter: coding]")
    print("    * SpecialistAgent(reason)  [Watches: /execution/{task}/v2 | Filter: reasoning]")
    print("    * ValidatorAgent           [Watches: /execution/{task}/v3]")

    # Start agents on parallel worker threads
    print("\n[+] Launching Distributed Agent Workers in Parallel:")
    threads = [
        threading.Thread(target=supervisor.run, args=(task_id,), name="supervisor-worker", daemon=True),
        threading.Thread(target=coding_spec.run, args=(task_id,), name="coding-spec-worker", daemon=True),
        threading.Thread(target=reasoning_spec.run, args=(task_id,), name="reasoning-spec-worker", daemon=True),
        threading.Thread(target=validator.run, args=(task_id,), name="validator-worker", daemon=True),
    ]

    for t in threads:
        t.start()
        print(f"    [+] {t.name}.start()")

    time.sleep(0.05)

    # Time=0ms: Submit task -> State v1
    start_time = time.time()
    print("\n--- TIME=0ms: Task Submitted ---")
    state_v1 = ExecutionState(version=1, task_id=task_id, input=task_input)
    key_v1 = f"/execution/{task_id}/v1"
    etcd.put(key_v1, json.dumps(state_v1.to_dict()).encode("utf-8"))
    print(f"[*] Stored State v1 in etcd: '{key_v1}'")
    print(f"    Payload: {json.dumps(state_v1.to_dict(), indent=2)}")

    # Wait for final State v4
    print("\n[*] Observing Linearizable State Transitions via etcd Watcher...")
    try:
        final_v4_dict = supervisor.wait_for_state(task_id, version=4, timeout=5.0)
        final_state = ExecutionState(**final_v4_dict)
    except TimeoutError:
        print("[!] Timeout waiting for State v4.")
        final_state = None

    elapsed_ms = (time.time() - start_time) * 1000
    print(f"\n[+] Distributed Execution Completed in {elapsed_ms:.1f}ms")

    # Inspect all linearizable state snapshots from etcd
    print_banner("ETCD STATE REPLICATION INSPECTION (/execution/{task_id}/v*)")
    entries = etcd.get_prefix(f"/execution/{task_id}/")
    for raw_bytes, meta in entries:
        d = json.loads(raw_bytes.decode("utf-8") if isinstance(raw_bytes, (bytes, bytearray)) else raw_bytes)
        v = d.get("version")
        k = meta.get("key", f"/execution/{task_id}/v{v}")
        print(f"\n>> Key: {k} (Version {v})")
        if v == 1:
            print(f"   Input:            {d.get('input')}")
        elif v == 2:
            print(f"   Routing Decision: {d.get('routing_decision')}")
        elif v == 3:
            print(f"   Specialist:       {d.get('routing_decision')}")
            print(f"   Output Snippet:   {d.get('specialist_output')[:160]}...")
        elif v == 4:
            status_tag = "VALIDATED (SUCCESS)" if d.get("validation_result") else "REJECTED"
            print(f"   Validation:       {status_tag}")
            print(f"   Reason:           {d.get('reason')}")

    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    run_distributed_state_demo()
