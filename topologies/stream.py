"""
Topology as Message Streams: Standalone Re-export and Entry Point.
"""

try:
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
except ImportError:
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

__all__ = [
    "ConsumerRecord",
    "InMemoryKafkaBroker",
    "KafkaProducer",
    "KafkaConsumer",
    "SupervisorAgent",
    "SpecialistAgent",
    "ValidatorAgent",
    "StreamPipeline",
    "run_message_stream_pipeline",
    "StreamTopology"
]
