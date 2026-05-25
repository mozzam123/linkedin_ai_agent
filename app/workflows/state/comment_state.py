from typing import TypedDict, Optional, List, Dict
from app.core.tracing import TraceCollector


class CommentWorkflowState(TypedDict):

    # ── Discovery node output ──────────────────────────────────────────────
    # Raw post data returned by the scraper before any filtering or scoring.
    # Each dict contains: post_url, author_name, author_linkedin_url,
    # post_text, post_type
    scraped_posts: Optional[List[Dict]]

    # ── Relevance node output ──────────────────────────────────────────────
    # All scraped posts after LLM scoring. Each dict carries the original
    # scraper keys plus: relevance_score, relevance_reason, skip_reason.
    # Posts that were filtered out are still in this list — they carry a
    # non-null skip_reason so the save node can record why they were skipped.
    scored_posts: Optional[List[Dict]]

    # Subset of scored_posts that passed the relevance threshold and all
    # hard filters (cooldown, already-commented, word count, etc.).
    # These are the posts the comment node will generate comments for.
    selected_posts: Optional[List[Dict]]

    # ── Comment generation node output ────────────────────────────────────
    # One dict per post that successfully produced an accepted comment.
    # Each dict contains: post_url, comment_text, self_score,
    # self_critique, is_generic, generation_attempt
    generated_comments: Optional[List[Dict]]

    # Subset of generated_comments whose self_score passed the
    # COMMENT_SELF_SCORE_THRESHOLD. These are saved to DB as
    # status='pending_approval' and shown in the Streamlit approval queue.
    approved_comments: Optional[List[Dict]]

    # ── Workflow metadata ──────────────────────────────────────────────────
    # Overall state of this workflow run. Drives conditional edges in the
    # graph. Values: 'starting' | 'discovery_done' | 'scoring_done' |
    # 'comments_generated' | 'completed' | 'failed'
    status: str

    # Non-fatal errors accumulated during the run. Individual node failures
    # (e.g. one post could not be scored) are appended here rather than
    # crashing the whole workflow. Fatal errors set status='failed'.
    run_errors: List[str]

    # ── Summary counts ─────────────────────────────────────────────────────
    # Populated progressively as each node runs. Used by the save node for
    # logging and by the comment service to build the return summary.
    # Keys: posts_scraped, posts_passed_filter, comments_generated,
    #       comments_passed_critique, saved_to_db
    stats: Optional[Dict]

    # ── Tracing ───────────────────────────────────────────────────────────
    # Same TraceCollector pattern used in LinkedInPostState. Each node calls
    # trace.log_step() with its name, inputs, outputs, and duration so the
    # full run can be inspected after completion.
    trace: TraceCollector