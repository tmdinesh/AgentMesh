from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True, index=True)
    category = Column(String(64), nullable=False, index=True)  # Reasoning, Question Answering, Decision/Summary
    title = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    evaluation_criteria = Column(Text, nullable=False)
    difficulty = Column(String(32), default="Medium")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    experiments = relationship("Experiment", back_populates="task", cascade="all, delete-orphan")
