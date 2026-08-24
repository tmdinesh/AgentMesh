from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    turn: int
    sender_id: str
    sender_role: str
    receiver_id: str
    receiver_role: str
    content: str
    model_name: Optional[str] = None
    provider: Optional[str] = None


class MessageCreate(MessageBase):
    id: str
    experiment_id: str
    timestamp: Optional[datetime] = None


class MessageResponse(MessageBase):
    id: str
    experiment_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
