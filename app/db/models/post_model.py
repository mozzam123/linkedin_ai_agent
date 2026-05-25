from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class LinkedInPost(Base):

    __tablename__ = "linkedin_posts"

    id = Column(Integer, primary_key=True, index=True)

    topic = Column(String)

    research_notes = Column(Text)

    generated_post = Column(Text)

    critique = Column(Text)

    score = Column(Float)

    final_post = Column(Text)

    status = Column(String)

    approved_by = Column(String, nullable=True)

    review_comments = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())