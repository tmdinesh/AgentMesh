"""
Topology with Distributed State: Standalone Re-export and Entry Point.
"""

try:
    from app.topologies.distributed_state import (
        ExecutionState,
        InMemoryEtcdClient,
        get_etcd_client,
        DistributedAgent,
        SupervisorAgent,
        SpecialistAgent,
        ValidatorAgent,
        DistributedStateTopology,
        run_distributed_state_pipeline
    )
except ImportError:
    from backend.app.topologies.distributed_state import (
        ExecutionState,
        InMemoryEtcdClient,
        get_etcd_client,
        DistributedAgent,
        SupervisorAgent,
        SpecialistAgent,
        ValidatorAgent,
        DistributedStateTopology,
        run_distributed_state_pipeline
    )

__all__ = [
    "ExecutionState",
    "InMemoryEtcdClient",
    "get_etcd_client",
    "DistributedAgent",
    "SupervisorAgent",
    "SpecialistAgent",
    "ValidatorAgent",
    "DistributedStateTopology",
    "run_distributed_state_pipeline"
]
