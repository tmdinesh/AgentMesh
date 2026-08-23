from typing import List, Tuple, Dict, Any
from app.topologies.base import BaseTopology, AgentInfo


class ChainTopology(BaseTopology):
    """
    Chain Topology:
    - Sequential pipelined communication: A1 -> A2 -> A3 -> ... -> An -> A1.
    - Each agent strictly passes context and refinement to the immediate successor in the sequence.
    """

    @property
    def name(self) -> str:
        return "CHAIN"

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False
        try:
            s_idx = self.agent_ids.index(sender_id)
            r_idx = self.agent_ids.index(receiver_id)
            # Allowed if receiver is immediately next in chain or wraps around
            return r_idx == (s_idx + 1) % len(self.agents)
        except ValueError:
            return False

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        try:
            s_idx = self.agent_ids.index(sender_id)
            next_idx = (s_idx + 1) % len(self.agents)
            return [self.agent_ids[next_idx]]
        except ValueError:
            return []

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        edges = []
        n = len(self.agents)
        for i in range(n):
            sender = self.agents[i].id
            receiver = self.agents[(i + 1) % n].id
            edges.append((sender, receiver))
        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        In turn_idx, agent i transmits to agent (i+1) % N.
        """
        n = len(self.agents)
        sender_idx = turn_idx % n
        receiver_idx = (sender_idx + 1) % n
        return [(self.agents[sender_idx], self.agents[receiver_idx])]
