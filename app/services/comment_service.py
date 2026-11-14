"""
Service layer for the comment workflow: run it, and manage the approval queue.

Phase 3 stops at "pending_approval". Nothing here posts to LinkedIn.
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.core.tracing import TraceCollector
from app.db.models.discovered_post_model import DiscoveredPost
from app.db.models.generated_comment_model import GeneratedComment
from app.db.session import SessionLocal
from app.workflows.graphs.comments_graph import comment_workflow


def run_comment_workflow(max_posts: int | None = None) -> dict:
    """
    Discover posts, score relevance, generate draft comments.

    Returns a summary: stats, errors, generated comments, trace.
    """
    original_cap = settings.MAX_POSTS_TO_SCRAPE_PER_RUN
    if max_posts:
        settings.MAX_POSTS_TO_SCRAPE_PER_RUN = int(max_posts)

    initial_state = {
        "scraped_posts": [],
        "scored_posts": [],
        "selected_posts": [],
        "generated_comments": [],
        "approved_comments": [],
        "status": "starting",
        "run_errors": [],
        "stats": {},
        "trace": TraceCollector(),
    }

    try:
        result = comment_workflow.invoke(initial_state)
    finally:
        settings.MAX_POSTS_TO_SCRAPE_PER_RUN = original_cap

    return {
        "status": result.get("status"),
        "stats": result.get("stats") or {},
        "errors": result.get("run_errors") or [],
        "generated": result.get("generated_comments") or [],
        "accepted": result.get("approved_comments") or [],
    }


# ── Approval queue ────────────────────────────────────────────────────────────

def pending_comments(limit: int = 50) -> list[dict]:
    """Comments waiting for review, newest first, with their source post."""
    db = SessionLocal()
    try:
        rows = (
            db.query(GeneratedComment, DiscoveredPost)
            .join(DiscoveredPost, GeneratedComment.discovered_post_id == DiscoveredPost.id)
            .filter(GeneratedComment.status == "pending_approval")
            .order_by(GeneratedComment.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "comment_id": comment.id,
                "post_id": post.id,
                "post_url": post.post_url,
                "author_name": post.author_name,
                "post_text": post.post_text,
                "comment_text": comment.comment_text,
                "self_score": comment.self_score,
                "self_critique": comment.self_critique,
                "created_at": comment.created_at,
            }
            for comment, post in rows
        ]
    finally:
        db.close()


def approve_comment(comment_id: int, edited_text: str | None = None) -> bool:
    """Mark a comment approved (optionally with your edited text). Nothing is posted."""
    db = SessionLocal()
    try:
        comment = db.query(GeneratedComment).filter(GeneratedComment.id == comment_id).first()
        if comment is None:
            return False
        if edited_text is not None and edited_text.strip():
            comment.comment_text = edited_text.strip()
            comment.comment_length = len(comment.comment_text)
        comment.status = "approved"
        comment.approved_at = datetime.now(timezone.utc)
        db.commit()
        return True
    finally:
        db.close()


def reject_comment(comment_id: int, reason: str = "Rejected during review") -> bool:
    db = SessionLocal()
    try:
        comment = db.query(GeneratedComment).filter(GeneratedComment.id == comment_id).first()
        if comment is None:
            return False
        comment.status = "rejected"
        comment.rejection_reason = reason
        db.commit()
        return True
    finally:
        db.close()


def approved_comments(limit: int = 50) -> list[dict]:
    """Approved comments waiting to be posted, with their source post."""
    db = SessionLocal()
    try:
        rows = (
            db.query(GeneratedComment, DiscoveredPost)
            .join(DiscoveredPost, GeneratedComment.discovered_post_id == DiscoveredPost.id)
            .filter(GeneratedComment.status == "approved")
            .order_by(GeneratedComment.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "comment_id": comment.id,
                "post_id": post.id,
                "post_url": post.post_url,
                "author_name": post.author_name,
                "post_text": post.post_text,
                "comment_text": comment.comment_text,
                "self_score": comment.self_score,
                "self_critique": comment.self_critique,
                "created_at": comment.created_at,
            }
            for comment, post in rows
        ]
    finally:
        db.close()
