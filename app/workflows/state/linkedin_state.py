from typing import TypedDict, Optional, List
from app.core.tracing import TraceCollector


class LinkedInPostState(TypedDict):
    topic: Optional[str]
    post_goal: Optional[str]          # IMPRESSIONS, COMMENTS, or SAVES
    research_notes: Optional[str]
    generated_post: Optional[str]
    critique: Optional[str]
    score: Optional[float]
    final_post: Optional[str]
    status: Optional[str]
    errors: List[str]
    validation_errors: List[str]
    is_valid: bool
    iteration_count: int
    trace: TraceCollector
    ai_research: Optional[str]
    startup_research: Optional[str]
    tools_research: Optional[str]