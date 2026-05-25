from datetime import datetime, timezone
from sqlalchemy import (Column,DateTime,Float,ForeignKey,Integer,String,Text, Boolean)
from app.db.session import Base


class GeneratedComment(Base):
    __tablename__ = "generated_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discovered_post_id = Column(Integer,ForeignKey("discovered_posts.id"),nullable=False,)
    comment_text = Column(Text, nullable=False)
    comment_length = Column(Integer, nullable=True)
    self_score = Column(Float, nullable=True)
    self_critique = Column(Text, nullable=True)
    is_generic = Column(Boolean, default=False, nullable=False)
    generation_attempt = Column(Integer,default=1,nullable=False,)
    status = Column(String,nullable=False,default="pending_approval",)
    rejection_reason = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    publish_error = Column(Text, nullable=True)
    created_at = Column(DateTime,default=lambda: datetime.now(timezone.utc),nullable=False,)