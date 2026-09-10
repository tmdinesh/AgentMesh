"""
Actor Topology for AgentMesh:
Independent actors with mailboxes, routing decisions, specialist execution, and validator auditing.

Communication Model:
1. SupervisorActor (Agent 1) receives tasks, evaluates routing logic, and sends RouteMessage to SpecialistActors.
2. SpecialistActors (Agent 2 .. N-1) process work requests concurrently and return ResultMessages.
3. ValidatorActor (Agent N) receives work output, validates correctness against criteria, and issues FinalResult.
4. Peer-to-peer lateral communication between specialists is restricted: all coordination occurs via mailboxes and messages.
"""

from typing import List, Tuple, Dict, Any, Optional
from app.topologies.base import BaseTopology, AgentInfo


class ActorTopology(BaseTopology):
    """
    Actor Topology:
    - Agent 1: SupervisorActor (Routing decision engine and coordinator)
    - Agents 2 .. N-1: SpecialistActors (Coding, Reasoning, Critic, Fact-Checker)
    - Agent N: ValidatorActor (Quality reviewer and acceptance criteria validator)
    """

    @property
    def name(self) -> str:
        return "ACTOR"

    @property
    def supervisor(self) -> AgentInfo:
        for a in self.agents:
            if a.is_central:
                return a
        return self.agents[0]

    @property
    def validator(self) -> AgentInfo:
        # Last agent in team acts as the dedicated ValidatorActor
        return self.agents[-1]

    @property
    def specialists(self) -> List[AgentInfo]:
        sup = self.supervisor
        val = self.validator
        return [a for a in self.agents if a.id != sup.id and a.id != val.id]

    def is_allowed_communication(self, sender_id: str, receiver_id: str) -> bool:
        if sender_id == receiver_id:
            return False

        sup_id = self.supervisor.id
        val_id = self.validator.id

        # 1. Supervisor <-> Specialist (RouteMessage / ResultMessage)
        if (sender_id == sup_id and receiver_id != val_id) or (receiver_id == sup_id and sender_id != val_id):
            return True

        # 2. Supervisor <-> Validator (FinalResult / Validation requests)
        if (sender_id == sup_id and receiver_id == val_id) or (sender_id == val_id and receiver_id == sup_id):
            return True

        # 3. Specialist -> Validator (Work submission for verification)
        if receiver_id == val_id and sender_id != sup_id:
            return True

        # Lateral Specialist <-> Specialist is disallowed
        return False

    def get_allowed_receivers(self, sender_id: str) -> List[str]:
        sup_id = self.supervisor.id
        val_id = self.validator.id

        if sender_id == sup_id:
            # Supervisor can message specialists and validator
            return [a.id for a in self.agents if a.id != sup_id]
        elif sender_id == val_id:
            # Validator reports back to supervisor
            return [sup_id]
        else:
            # Specialist reports to supervisor and validator
            return [sup_id, val_id]

    def get_graph_edges(self) -> List[Tuple[str, str]]:
        edges = []
        sup_id = self.supervisor.id
        val_id = self.validator.id

        for spec in self.specialists:
            # Supervisor <-> Specialist bidirectional
            edges.append((sup_id, spec.id))
            edges.append((spec.id, sup_id))
            # Specialist -> Validator
            edges.append((spec.id, val_id))

        # Supervisor <-> Validator bidirectional
        edges.append((sup_id, val_id))
        edges.append((val_id, sup_id))

        return edges

    def plan_turn(self, turn_idx: int, message_history: List[Dict[str, Any]]) -> List[Tuple[AgentInfo, AgentInfo]]:
        """
        Plans actor turn interactions:
        - Phase 1 (Turn 0): Supervisor routes to Primary Specialist.
        - Phase 2 (Turn 1): Specialist processes and responds to Supervisor / forwards to Validator.
        - Phase 3 (Turn 2): Validator checks output and issues validation verdict to Supervisor.
        - Subsequent turns: Iterative review / consultation with secondary specialists (e.g. Critic).
        """
        sup = self.supervisor
        val = self.validator
        specs = self.specialists if self.specialists else [self.agents[1]]

        phase = turn_idx % 3

        if phase == 0:
            # Supervisor -> Specialist (RouteMessage)
            spec_idx = (turn_idx // 3) % len(specs)
            return [(sup, specs[spec_idx])]
        elif phase == 1:
            # Specialist -> Supervisor or Validator (ResultMessage)
            spec_idx = (turn_idx // 3) % len(specs)
            return [(specs[spec_idx], sup)]
        else:
            # Validator -> Supervisor (FinalResult)
            return [(val, sup)]
