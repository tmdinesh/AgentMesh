import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), ForeignKey("tasks.id"), nullable=False, index=True)
    topology = Column(String(32), nullable=False, index=True)  # STAR, CHAIN, MESH
    num_agents = Column(Integer, nullable=False, default=5)
    max_turns = Column(Integer, nullable=False, default=10)
    turns_taken = Column(Integer, default=0)
    
    success = Column(Boolean, nullable=False, default=False)
    final_answer = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    failure_type = Column(String(64), nullable=False, default="No Failure", index=True)
    failure_reason = Column(Text, nullable=True)
    
    total_messages = Column(Integer, default=0)
    network_metrics_json = Column(Text, nullable=True)
    is_mock = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    task = relationship("Task", back_populates="experiments")
    messages = relationship("Message", back_populates="experiment", cascade="all, delete-orphan", order_by="Message.turn")

    @property
    def network_metrics(self):
        if self.network_metrics_json:
            try:
                return json.loads(self.network_metrics_json)
            except Exception:
                return {}
        return {}

    @network_metrics.setter
    def network_metrics(self, val):
        if isinstance(val, (dict, list)):
            self.network_metrics_json = json.dumps(val)
        elif isinstance(val, str):
            self.network_metrics_json = val
        else:
            self.network_metrics_json = "{}"
