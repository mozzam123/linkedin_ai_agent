from datetime import datetime, timezone
from sqlalchemy import (Column,DateTime,Float,Integer,String,Text, Boolean)
from app.db.session import Base


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    linkedin_url = Column(String,nullable=False,unique=True,)
    name = Column(String, nullable=True)
    total_comments_made = Column(Integer,default=0,nullable=False,)
    last_commented_at = Column(DateTime,nullable=True,)
    avg_relevance_score = Column(Float,nullable=True,)
    topics_seen = Column(Text,nullable=True,)
    is_blocked = Column(Boolean,default=False,nullable=False,)
    created_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),nullable=False,)
    updated_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc),nullable=False,)