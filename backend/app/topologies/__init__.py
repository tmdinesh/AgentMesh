from app.topologies.base import BaseTopology, AgentInfo
from app.topologies.star import StarTopology
from app.topologies.chain import ChainTopology
from app.topologies.mesh import MeshTopology
from app.topologies.tree import TreeTopology
from app.topologies.emergent import EmergentTopology

TOPOLOGY_MAP = {
    "STAR": StarTopology,
    "CHAIN": ChainTopology,
    "MESH": MeshTopology,
    "TREE": TreeTopology,
    "UNCONSTRAINED": EmergentTopology,
    "EMERGENT": EmergentTopology
}


def get_topology_instance(topology_name: str, agents: list[AgentInfo]) -> BaseTopology:
    norm_name = topology_name.upper()
    if norm_name not in TOPOLOGY_MAP:
        raise ValueError(f"Unknown topology '{topology_name}'. Allowed: {list(TOPOLOGY_MAP.keys())}")
    return TOPOLOGY_MAP[norm_name](agents)
