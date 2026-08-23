import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.experiment import Experiment
from app.models.message import Message
from app.schemas.experiment import ExperimentCreate, BatchExperimentCreate
from app.topologies import get_topology_instance, BaseTopology
from app.services.agent_service import create_agent_team, get_agent_prompt
from app.services.llm_service import llm_service
from app.services.evaluation_service import evaluation_service
from app.services.network_analysis import network_analysis_service
from app.config import settings

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    Coordinates and executes multi-agent topology experiments with heterogeneous LLMs.
    """

    async def run_experiment(self, payload: ExperimentCreate, db: Session) -> Experiment:
        task = db.query(Task).filter(Task.id == payload.task_id).first()
        if not task:
            raise ValueError(f"Task with ID '{payload.task_id}' not found.")

        # 1. Initialize Agents with dedicated model configurations
        agents = create_agent_team(num_agents=payload.num_agents)

        # 2. Initialize Topology Engine
        topo_name = payload.topology.upper()
        topology: BaseTopology = get_topology_instance(topo_name, agents)

        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)

        recorded_messages: List[Dict[str, Any]] = []
        db_messages: List[Message] = []

        # 3. Communication Loop
        turns_to_run = min(payload.max_turns, 20)

        for turn_idx in range(turns_to_run):
            planned_interactions = topology.plan_turn(turn_idx=turn_idx, message_history=recorded_messages)
            is_final = (turn_idx == turns_to_run - 1)

            for sender, receiver in planned_interactions:
                # Rigorous topology permission verification
                if not topology.is_allowed_communication(sender.id, receiver.id):
                    logger.warning(f"Communication from {sender.id} to {receiver.id} denied by topology {topo_name}!")
                    continue

                # Filter context based on topology visibility
                visible_history = topology.filter_visible_messages(sender.id, recorded_messages)

                # Generate agent message with dedicated agent LLM
                system_prompt = get_agent_prompt(sender.role)
                content, model_name, provider = await llm_service.generate_agent_message(
                    agent_id=sender.id,
                    agent_role=sender.role,
                    system_prompt=system_prompt,
                    task_question=task.question,
                    sender_role=sender.role,
                    receiver_role=receiver.role,
                    visible_dialogue=visible_history,
                    turn=turn_idx + 1,
                    topology_name=topo_name,
                    is_final_turn=is_final
                )

                msg_id = f"msg_{uuid.uuid4().hex[:10]}"
                msg_dict = {
                    "id": msg_id,
                    "experiment_id": experiment_id,
                    "turn": turn_idx + 1,
                    "sender_id": sender.id,
                    "sender_role": sender.role,
                    "receiver_id": receiver.id,
                    "receiver_role": receiver.role,
                    "content": content,
                    "model_name": model_name,
                    "provider": provider,
                    "timestamp": datetime.now(timezone.utc)
                }

                recorded_messages.append(msg_dict)
                db_messages.append(Message(**msg_dict))

        # 4. Final Answer Synthesis
        final_answer = await llm_service.synthesize_final_answer(
            task_question=task.question,
            all_messages=recorded_messages,
            topology_name=topo_name
        )

        # 5. Two-Stage Evaluation & Failure Classification
        success, failure_type, failure_reason = await evaluation_service.evaluate_experiment(
            task_question=task.question,
            expected_answer=task.expected_answer,
            evaluation_criteria=task.evaluation_criteria,
            final_answer=final_answer,
            dialogue_history=recorded_messages,
            topology_name=topo_name
        )

        # 6. NetworkX Analysis
        topology_edges = topology.get_graph_edges()
        network_metrics = network_analysis_service.analyze_experiment_network(
            agents=agents,
            messages=recorded_messages,
            topology_edges=topology_edges
        )

        # 7. Persist to Database
        exp = Experiment(
            id=experiment_id,
            task_id=task.id,
            topology=topo_name,
            num_agents=payload.num_agents,
            max_turns=payload.max_turns,
            turns_taken=turns_to_run,
            success=success,
            final_answer=final_answer,
            expected_answer=task.expected_answer,
            failure_type=failure_type,
            failure_reason=failure_reason,
            total_messages=len(recorded_messages),
            is_mock=settings.is_mock_enabled if payload.use_mock is None else payload.use_mock,
            created_at=created_at
        )
        exp.network_metrics = network_metrics.model_dump()

        db.add(exp)
        for msg in db_messages:
            db.add(msg)

        db.commit()
        db.refresh(exp)
        return exp

    async def run_batch_experiments(self, payload: BatchExperimentCreate, db: Session) -> List[Experiment]:
        """Runs batch repetitions across selected topologies for statistical power."""
        results = []
        for topo in payload.topologies:
            for rep in range(payload.repetitions):
                single_req = ExperimentCreate(
                    task_id=payload.task_id,
                    topology=topo,
                    num_agents=payload.num_agents,
                    max_turns=payload.max_turns,
                    use_mock=payload.use_mock
                )
                exp = await self.run_experiment(single_req, db)
                results.append(exp)
        return results


experiment_service = ExperimentService()
