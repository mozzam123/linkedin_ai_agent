from datetime import datetime, timezone

from sqlalchemy import (Column,DateTime,Float,ForeignKey,Integer,String,Text)

from app.db.session import Base


class DiscoveredPost(Base):
    __tablename__ = "discovered_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_url = Column(String, nullable=False, unique=True)
    author_name = Column(String, nullable=True)
    author_linkedin_url = Column(String, nullable=True)
    post_text = Column(Text, nullable=False)
    post_type = Column(String, nullable=True)
    scraped_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),nullable=False,)
    relevance_score = Column(Float, nullable=True)
    relevance_reason = Column(Text, nullable=True)
    status = Column(String,nullable=False,default="scraped",)
    skip_reason = Column(String, nullable=True)
    created_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),nullable=False,)