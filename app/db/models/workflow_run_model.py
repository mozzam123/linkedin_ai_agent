from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime

from app.db.session import Base


class WorkflowRun(Base):

    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)

    topic = Column(String)

    status = Column(String)  # running / completed / failed

    final_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    duration_seconds = Column(Float)

    trace = Column(Text)  # JSON string of full execution trace