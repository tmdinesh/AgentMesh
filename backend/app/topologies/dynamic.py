from typing import List, Tuple, Dict, Any, Optional, Set
from app.topologies.base import BaseTopology, AgentInfo

class TelemetryMonitor:
    """
    Monitors Social Network Analysis (SNA) metrics during agent execution.
    Specifically tracks Message Volume (V_msg) and Coordinator Betweenness (C_B).
    """
    def __init__(self, tau_volume: int = 2000, tau_dom: float = 0.45):
        self.tau_volume = tau_volume
        self.tau_dom = tau_dom
        self.message_volumes: Dict[str, int] = {}
        self.coordinator_betweenness: Dict[str, float] = {}

    def update(self, message_history: List[Dict[str, Any]]):
        self.message_volumes.clear()
        self.coordinator_betweenness.clear()
        
        total_msgs = len(message_history)
        if total_msgs == 0:
            return

        for msg in message_history:
            sender = msg.get("sender_id")
            receiver = msg.get("receiver_id")
            tokens = msg.get("tokens", 150) # Fallback if tokens aren't explicitly tracked
            
            if sender:
                self.message_volumes[sender] = self.message_volumes.get(sender, 0) + tokens
                # Simplified Betweenness calculation based on message involvement
                self.coordinator_betweenness[sender] = self.coordinator_betweenness.get(sender, 0.0) + 1.0 / total_msgs
                
            if receiver and receiver != "ALL":
                self.coordinator_betweenness[receiver] = self.coordinator_betweenness.get(receiver, 0.0) + 1.0 / total_msgs


class DynamicTopology(BaseTopology):
    """
    AgentMesh Dynamic Topology Optimization Algorithm.
    Dynamically rewires communication graphs based on real-time telemetry (V_msg, C_B)
    to prevent Groupthink and infinite deliberation loops.
    """
    def __init__(self, agents: List[AgentInfo], tau_volume: int = 2000, tau_dom: float = 0.45):
        super().__init__(agents)
        self.telemetry = TelemetryMonitor(tau_volume, tau_dom)
        
        # Start fully connected
        self._current_edges: Set[Tuple[str, str]] = set()
        for a in agents:
            for b in agents:
                if a.id != b.id:
                    self._current_edges.add((a.id, b.id))
                    
        self._critic_injected = False
        self._pruned_agents: Set[str] = set()

    @property
    def name(self) -> str:
        return "DYNAMIC"

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id in self._pruned_agents or receiver_id in self._pruned_agents:
            return False
        return (sender_id, receiver_id) in self._current_edges or receiver_id == "ALL"

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        if sender_id in self._pruned_agents:
            return []
        return [b for a, b in self._current_edges if a == sender_id and b not in self._pruned_agents]

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        return [e for e in self._current_edges if e[0] not in self._pruned_agents and e[1] not in self._pruned_agents]

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Dynamically plan the next turn, rewiring the topology if thresholds are breached.
        """
        self.telemetry.update(message_history)
        
        # 1. Check V_msg Threshold (tau_volume) -> Early Termination / Pruning
        for agent_id, vol in self.telemetry.message_volumes.items():
            if vol > self.telemetry.tau_volume and agent_id not in self._pruned_agents:
                # Prune branch to prevent infinite loop
                self._pruned_agents.add(agent_id)
                # Remove edges associated with pruned agent
                edges_to_remove = [(u, v) for u, v in self._current_edges if u == agent_id or v == agent_id]
                for edge in edges_to_remove:
                    self._current_edges.remove(edge)
                
        # 2. Check C_B Threshold (tau_dom) -> Groupthink Prevention (Critic Injection)
        for agent_id, cb in self.telemetry.coordinator_betweenness.items():
            if cb > self.telemetry.tau_dom and not self._critic_injected and agent_id not in self._pruned_agents:
                # Inject a Critic Agent mid-deliberation
                critic = AgentInfo(
                    agent_id=f"critic_{turn_idx}", 
                    name="DynamicCritic", 
                    role="critic", 
                    model_name="qwen3_30b",
                    is_local=True
                )
                self.agents.append(critic)
                self.agent_map[critic.id] = critic
                
                # Rewire: connect critic directly to the dominant coordinator
                self._current_edges.add((critic.id, agent_id))
                self._current_edges.add((agent_id, critic.id))
                self._critic_injected = True
                
                # Prioritize critic interaction in this turn
                return [(critic, self.agent_map[agent_id])]
                
        # 3. Default fallback (Round Robin on active mesh)
        active_agents = [a for a in self.agents if a.id not in self._pruned_agents]
        n = len(active_agents)
        
        if n <= 1:
            return [] # No valid pairs left
            
        sender_idx = turn_idx % n
        target_offset = 1 + ((turn_idx // n) % (n - 1))
        receiver_idx = (sender_idx + target_offset) % n
        
        sender = active_agents[sender_idx]
        receiver = active_agents[receiver_idx]
        
        # Ensure edge exists, if not, find one that does
        if (sender.id, receiver.id) in self._current_edges:
            return [(sender, receiver)]
            
        # Fallback to any valid edge
        for u, v in self._current_edges:
            if u not in self._pruned_agents and v not in self._pruned_agents:
                return [(self.agent_map[u], self.agent_map[v])]
                
        return []
