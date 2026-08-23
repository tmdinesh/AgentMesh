from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    id: str
    category: str
    title: str
    question: str
    expected_answer: str
    evaluation_criteria: str
    difficulty: Optional[str] = "Medium"


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
