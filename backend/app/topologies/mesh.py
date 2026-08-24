from typing import List, Tuple, Dict, Any
from app.topologies.base import BaseTopology, AgentInfo


class MeshTopology(BaseTopology):
    """
    Mesh Topology:
    - Fully connected network (all-to-all).
    - Every agent is authorized to communicate directly with any other agent.
    """

    @property
    def name(self) -> str:
        return "MESH"

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False
        return sender_id in self.agent_map and (receiver_id in self.agent_map or receiver_id == "ALL")

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        if sender_id not in self.agent_map:
            return []
        return [a.id for a in self.agents if a.id != sender_id]

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        edges = []
        for a in self.agents:
            for b in self.agents:
                if a.id != b.id:
                    edges.append((a.id, b.id))
        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Mesh turn execution:
        In each turn, a sender agent engages a target peer in a peer-to-peer round-robin fashion.
        """
        n = len(self.agents)
        # Pair generation across rounds
        sender_idx = turn_idx % n
        # Target rotates so all pairs get actively engaged over turns
        target_offset = 1 + ((turn_idx // n) % (n - 1))
        receiver_idx = (sender_idx + target_offset) % n

        return [(self.agents[sender_idx], self.agents[receiver_idx])]
