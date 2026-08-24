from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, index=True)
    experiment_id = Column(String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    turn = Column(Integer, nullable=False)
    sender_id = Column(String(64), nullable=False)
    sender_role = Column(String(64), nullable=False)
    receiver_id = Column(String(64), nullable=False)
    receiver_role = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    model_name = Column(String(64), nullable=True)
    provider = Column(String(32), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    experiment = relationship("Experiment", back_populates="messages")
