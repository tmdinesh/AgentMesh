from typing import List, Tuple, Dict, Any, Optional
from app.topologies.base import BaseTopology, AgentInfo


class TreeTopology(BaseTopology):
    """
    Tree Topology (Hierarchical Branching Graph):
    - Level 0 (Root): Agent 1 (Coordinator)
    - Level 1 (Branch Supervisors): Agent 2 (Solver) and Agent 3 (Critic)
    - Level 2 (Leaf Specialists): Agent 4 (Fact Checker -> under Agent 2), Agent 5 (Alternative Solver -> under Agent 3)
      and Agent 6 (Final Reviewer -> under Agent 1)
    - Communication is strictly allowed vertically between parents and direct children (Parent <-> Child).
    - Lateral cross-branch communication (e.g., Leaf to Leaf or Branch to Branch) is prohibited.
    """

    @property
    def name(self) -> str:
        return "TREE"

    def _get_parent_child_map(self) -> Dict[str, List[str]]:
        """Constructs parent-to-children mapping based on current agent IDs."""
        agent_ids = [a.id for a in self.agents]
        mapping: Dict[str, List[str]] = {aid: [] for aid in agent_ids}

        # Root: agent_1
        if "agent_1" in mapping:
            if "agent_2" in mapping:
                mapping["agent_1"].append("agent_2")
            if "agent_3" in mapping:
                mapping["agent_1"].append("agent_3")
            if "agent_6" in mapping:
                mapping["agent_1"].append("agent_6")

        # Branch 1: agent_2 -> agent_4
        if "agent_2" in mapping and "agent_4" in mapping:
            mapping["agent_2"].append("agent_4")

        # Branch 2: agent_3 -> agent_5
        if "agent_3" in mapping and "agent_5" in mapping:
            mapping["agent_3"].append("agent_5")

        return mapping

    def _get_parent(self, child_id: str) -> Optional[str]:
        pc_map = self._get_parent_child_map()
        for parent, children in pc_map.items():
            if child_id in children:
                return parent
        return None

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False
        pc_map = self._get_parent_child_map()
        # Direct parent -> child OR child -> parent
        is_child = receiver_id in pc_map.get(sender_id, [])
        is_parent = sender_id in pc_map.get(receiver_id, [])
        return is_child or is_parent

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        pc_map = self._get_parent_child_map()
        children = pc_map.get(sender_id, [])
        parent = self._get_parent(sender_id)
        receivers = list(children)
        if parent:
            receivers.append(parent)
        return receivers

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        pc_map = self._get_parent_child_map()
        edges = []
        for parent, children in pc_map.items():
            for child in children:
                edges.append((parent, child))
                edges.append((child, parent))
        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Hierarchical turn scheduling:
        - Downward delegation waves (Root -> Branch, Branch -> Leaf)
        - Upward reporting waves (Leaf -> Branch, Branch -> Root)
        """
        agent_dict = {a.id: a for a in self.agents}
        interactions: List[Tuple[AgentInfo, AgentInfo]] = []

        pc_map = self._get_parent_child_map()
        
        # Flatten parent-child pairs
        downward_pairs = []
        for parent, children in pc_map.items():
            for child in children:
                if parent in agent_dict and child in agent_dict:
                    downward_pairs.append((agent_dict[parent], agent_dict[child]))

        upward_pairs = []
        for parent, children in pc_map.items():
            for child in children:
                if parent in agent_dict and child in agent_dict:
                    upward_pairs.append((agent_dict[child], agent_dict[parent]))

        # Alternate downward delegation vs upward reporting
        if turn_idx % 2 == 0 and downward_pairs:
            pair = downward_pairs[(turn_idx // 2) % len(downward_pairs)]
            interactions.append(pair)
        elif upward_pairs:
            pair = upward_pairs[(turn_idx // 2) % len(upward_pairs)]
            interactions.append(pair)

        return interactions
