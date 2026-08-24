from typing import List, Tuple, Dict, Any
from app.topologies.base import BaseTopology, AgentInfo


class EmergentTopology(BaseTopology):
    """
    Unconstrained / Emergent Topology:
    - No static communication bottlenecks or enforced structural routing.
    - Agents self-organize dynamically based on conversational context, peer challenges, and audits.
    - All-to-all communication is fully permissible with unrestricted context visibility.
    """

    @property
    def name(self) -> str:
        return "UNCONSTRAINED"

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

    def filter_visible_messages(self, agent_id: str, message_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """In an unconstrained emergent network, all agents have full organic perception of the dialogue."""
        return list(message_history)

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Dynamic emergent turn planning:
        - Self-organizing routing based on communicative necessity and role interactions.
        - Dynamically pairs agents depending on deliberation phase (decomposition -> solving -> critique -> auditing -> synthesis).
        """
        n = len(self.agents)
        if n < 2:
            return []

        # Find agents by standard role identifiers if present
        coordinator = next((a for a in self.agents if "coordinator" in a.role.lower()), self.agents[0])
        solver = next((a for a in self.agents if "solver" in a.role.lower() and "alt" not in a.role.lower()), self.agents[min(1, n - 1)])
        critic = next((a for a in self.agents if "critic" in a.role.lower()), self.agents[min(2, n - 1)])
        fact_checker = next((a for a in self.agents if "fact" in a.role.lower()), self.agents[min(3, n - 1)])
        alt_solver = next((a for a in self.agents if "alt" in a.role.lower()), None)
        reviewer = next((a for a in self.agents if "review" in a.role.lower()), None)

        if turn_idx == 0:
            # Coordinator initiates and queries primary Solver
            return [(coordinator, solver)]
        elif turn_idx == 1:
            # Solver presents hypothesis to Critic for falsification
            return [(solver, critic)]
        elif turn_idx == 2:
            # Critic challenges Solver or prompts Fact Checker
            return [(critic, fact_checker)]
        elif turn_idx == 3:
            # Fact Checker validates constraints and responds to Coordinator / Solver
            return [(fact_checker, solver)]
        elif turn_idx == 4 and alt_solver:
            # Alternative Solver proposes competing heuristic to Coordinator
            return [(alt_solver, coordinator)]
        elif turn_idx == 5 and reviewer:
            # Final Reviewer audits deductions with Critic
            return [(reviewer, critic)]
        else:
            # Organic adaptive rotation across active peers
            sender_idx = turn_idx % n
            # Dynamic target selection ensuring cross-functional interaction
            target_idx = (sender_idx + 1 + (turn_idx // n)) % n
            if target_idx == sender_idx:
                target_idx = (sender_idx + 1) % n
            return [(self.agents[sender_idx], self.agents[target_idx])]
