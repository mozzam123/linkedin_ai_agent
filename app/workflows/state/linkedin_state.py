from typing import TypedDict, Optional, List
from app.core.tracing import TraceCollector


class LinkedInPostState(TypedDict):
    topic: Optional[str]
    research_notes: Optional[str]
    generated_post: Optional[str]
    critique: Optional[str]
    score: Optional[float]
    final_post: Optional[str]
    status: Optional[str]
    errors: List[str]
    validation_errors: List[str]  #  Tracks formatting/spam violations
    is_valid: bool                 #  True if passes all safety checks
    iteration_count: int
    trace: TraceCollector
    ai_research: Optional[str]
    startup_research: Optional[str]
    tools_research: Optional[str]