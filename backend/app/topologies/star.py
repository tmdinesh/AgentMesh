from typing import List, Tuple, Dict, Any
from app.topologies.base import BaseTopology, AgentInfo


class StarTopology(BaseTopology):
    """
    Star Topology:
    - Agent 1 (Coordinator) is the central hub.
    - Central hub communicates bidirectionally with each peripheral agent (A1 <-> Ai).
    - Peripheral agents cannot communicate directly with each other (Ai </-> Aj).
    """

    @property
    def name(self) -> str:
        return "STAR"

    @property
    def central_agent(self) -> AgentInfo:
        for a in self.agents:
            if a.is_central:
                return a
        return self.agents[0]

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False
        central_id = self.central_agent.id
        return sender_id == central_id or receiver_id == central_id

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        central_id = self.central_agent.id
        if sender_id == central_id:
            return [a.id for a in self.agents if a.id != central_id]
        else:
            return [central_id]

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        central_id = self.central_agent.id
        edges = []
        for a in self.agents:
            if a.id != central_id:
                edges.append((central_id, a.id))
                edges.append((a.id, central_id))
        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Alternates between:
        - Even turns (0, 2, ...): Central hub sends instructions/prompts to peripheral agents.
        - Odd turns (1, 3, ...): Peripheral agents send analysis/critiques back to central hub.
        """
        central = self.central_agent
        peripherals = [a for a in self.agents if a.id != central.id]
        interactions = []

        if turn_idx % 2 == 0:
            # Central sends to a peripheral agent in rotation
            target_idx = (turn_idx // 2) % len(peripherals)
            interactions.append((central, peripherals[target_idx]))
        else:
            # Peripheral responds back to central
            sender_idx = (turn_idx // 2) % len(peripherals)
            interactions.append((peripherals[sender_idx], central))

        return interactions
