"""
Topologies Package for AgentMesh / MAST Topology Lab.
"""

try:
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
        run_distributed_topology,
        ray_init,
        ray_shutdown,
        HAS_RAY
    )
    from app.topologies.actor import ActorTopology
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
    from app.topologies.distributed_state import (
        ExecutionState,
        InMemoryEtcdClient,
        get_etcd_client,
        DistributedAgent,
        DistributedStateTopology,
        run_distributed_state_pipeline
    )
except ImportError:
    from backend.app.topologies.actor_system import (
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
        run_distributed_topology,
        ray_init,
        ray_shutdown,
        HAS_RAY
    )
    from backend.app.topologies.actor import ActorTopology
    from backend.app.topologies.stream import (
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
    from backend.app.topologies.distributed_state import (
        ExecutionState,
        InMemoryEtcdClient,
        get_etcd_client,
        DistributedAgent,
        DistributedStateTopology,
        run_distributed_state_pipeline
    )

__all__ = [
    "Actor",
    "Message",
    "TaskRequest",
    "RouteMessage",
    "ResultMessage",
    "FinalResult",
    "Mailbox",
    "SupervisorActor",
    "SpecialistActor",
    "ValidatorActor",
    "ActorSystem",
    "get_llm_client",
    "run_distributed_topology",
    "ray_init",
    "ray_shutdown",
    "HAS_RAY",
    "ActorTopology",
    "ConsumerRecord",
    "InMemoryKafkaBroker",
    "KafkaProducer",
    "KafkaConsumer",
    "SupervisorAgent",
    "SpecialistAgent",
    "ValidatorAgent",
    "StreamPipeline",
    "run_message_stream_pipeline",
    "StreamTopology",
    "ExecutionState",
    "InMemoryEtcdClient",
    "get_etcd_client",
    "DistributedAgent",
    "DistributedStateTopology",
    "run_distributed_state_pipeline"
]
