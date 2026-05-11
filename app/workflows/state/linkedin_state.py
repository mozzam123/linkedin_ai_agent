from typing import TypedDict, Optional, List


class LinkedInPostState(TypedDict):
    topic: Optional[str]

    research_notes: Optional[str]

    generated_post: Optional[str]

    critique: Optional[str]

    score: Optional[float]

    final_post: Optional[str]

    status: Optional[str]

    errors: List[str]

    iteration_count: int