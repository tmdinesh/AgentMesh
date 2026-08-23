from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional


class AgentInfo:
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        is_central: bool = False,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        is_local: bool = False
    ):
        self.id = agent_id
        self.name = name
        self.role = role
        self.is_central = is_central
        self.model_name = model_name
        self.provider = provider
        self.is_local = is_local

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "is_central": self.is_central,
            "model_name": self.model_name,
            "provider": self.provider,
            "is_local": self.is_local
        }


class BaseTopology(ABC):
    """
    Abstract Base Class for multi-agent communication topologies.
    Enforces communication rules, graph edge sets, and turn routing.
    """

    def __init__(self, agents: List[AgentInfo]):
        self.agents = agents
        self.agent_map = {a.id: a for a in agents}
        self.agent_ids = [a.id for a in agents]

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        """Determines if a direct communication link from sender to receiver is permitted."""
        pass

    @abstractmethod
    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        """Returns list of agent IDs that the sender can transmit messages to."""
        pass

    @abstractmethod
    def get_graph_edges(self) -> List[Tuple[str, str]]:
        """Returns the static directed edge pairs (source, target) defined by this topology."""
        pass

    @abstractmethod
    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Determines which (sender, receiver) interactions take place in a given turn index.
        Returns a list of (sender, receiver) agent tuples for this turn round.
        """
        pass

    def filter_visible_messages(self, agent_id: str, message_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters message history so that an agent only sees messages they are topologically
        authorized to perceive (either messages sent by them or sent directly to them,
        or broadcast if topology rules allow).
        """
        visible = []
        for msg in message_history:
            sender = msg.get("sender_id")
            receiver = msg.get("receiver_id")
            
            # If agent was sender or direct receiver
            if sender == agent_id or receiver == agent_id:
                visible.append(msg)
            elif receiver == "ALL" and self.is_allowed_communication(sender, agent_id):
                visible.append(msg)
        return visible
