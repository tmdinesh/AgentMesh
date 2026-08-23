from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.message import MessageResponse
from app.schemas.network import NetworkMetrics
from app.schemas.task import TaskResponse


class ExperimentCreate(BaseModel):
    task_id: str
    topology: str = Field(..., description="STAR, CHAIN, MESH, or UNCONSTRAINED (EMERGENT)")
    num_agents: int = Field(5, ge=4, le=6, description="Number of agents: 4, 5, or 6")
    max_turns: int = Field(10, ge=1, le=25, description="Maximum communication turns")
    use_mock: Optional[bool] = None


class BatchExperimentCreate(BaseModel):
    task_id: str
    topologies: List[str] = ["STAR", "CHAIN", "MESH", "UNCONSTRAINED"]
    num_agents: int = 5
    max_turns: int = 8
    repetitions: int = Field(3, ge=1, le=10, description="Repetitions per topology")
    use_mock: Optional[bool] = None


class ExperimentResponse(BaseModel):
    id: str
    task_id: str
    topology: str
    num_agents: int
    max_turns: int
    turns_taken: int
    success: bool
    final_answer: Optional[str] = None
    expected_answer: Optional[str] = None
    failure_type: str
    failure_reason: Optional[str] = None
    total_messages: int
    is_mock: bool
    created_at: datetime
    network_metrics: Optional[Dict[str, Any]] = None
    task: Optional[TaskResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ExperimentDetailResponse(ExperimentResponse):
    messages: List[MessageResponse] = []
