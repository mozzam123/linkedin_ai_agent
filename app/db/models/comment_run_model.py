from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class CommentRun(Base):
    """One execution of the scheduled comment scan."""

    __tablename__ = "comment_runs"

    id = Column(Integer, primary_key=True, index=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    status = Column(String, default="running")  # running | completed | failed

    posts_scraped = Column(Integer, default=0)
    posts_new = Column(Integer, default=0)
    posts_selected = Column(Integer, default=0)
    comments_generated = Column(Integer, default=0)
    comments_accepted = Column(Integer, default=0)

    errors = Column(Text, nullable=True)
