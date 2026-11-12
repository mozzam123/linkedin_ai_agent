"""
Scheduled comment scanning (Phase 5).

One cycle = discover posts, score relevance, draft comments, record the run.
It never posts anything: posting stays a deliberate action in the UI.

Usage:
    poetry run python -m app.services.comment_scheduler            # run if due
    poetry run python -m app.services.comment_scheduler --force    # run now
    poetry run python -m app.services.comment_scheduler --max-posts 5

Exit codes: 0 = ran or not due, 1 = failed.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models.comment_run_model import CommentRun
from app.db.session import SessionLocal
from app.services.comment_service import run_comment_workflow


def _utcnow() -> datetime:
    """Naive UTC, matching the timestamps stored elsewhere in the DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def last_run() -> CommentRun | None:
    db = SessionLocal()
    try:
        return db.query(CommentRun).order_by(CommentRun.id.desc()).first()
    finally:
        db.close()


def is_due(now: datetime | None = None) -> bool:
    """True when SCHEDULER_INTERVAL_HOURS (plus jitter) has passed since the last run."""
    now = now or _utcnow()
    previous = last_run()
    if previous is None or previous.started_at is None:
        return True

    # Jitter is derived from the run id so it is stable rather than random per tick
    jitter = 0
    if settings.SCHEDULER_JITTER_SECONDS:
        random.seed(previous.id)
        jitter = random.randint(0, settings.SCHEDULER_JITTER_SECONDS)

    due_at = previous.started_at + timedelta(
        hours=settings.SCHEDULER_INTERVAL_HOURS, seconds=jitter
    )
    return now >= due_at


def next_run_at() -> datetime | None:
    previous = last_run()
    if previous is None:
        return None
    jitter = 0
    if settings.SCHEDULER_JITTER_SECONDS:
        random.seed(previous.id)
        jitter = random.randint(0, settings.SCHEDULER_JITTER_SECONDS)
    return previous.started_at + timedelta(
        hours=settings.SCHEDULER_INTERVAL_HOURS, seconds=jitter
    )


def run_cycle(max_posts: int | None = None, force: bool = False) -> dict:
    """Run one discovery + drafting cycle and record it."""
    if not force and not is_due():
        upcoming = next_run_at()
        return {
            "ran": False,
            "reason": f"Not due yet — next run at {upcoming:%Y-%m-%d %H:%M} UTC"
            if upcoming
            else "Not due yet",
        }

    started = time.time()
    db = SessionLocal()
    run = CommentRun(started_at=_utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id
    db.close()

    try:
        result = run_comment_workflow(max_posts=max_posts)
    except Exception as e:
        db = SessionLocal()
        try:
            row = db.query(CommentRun).filter(CommentRun.id == run_id).first()
            row.status = "failed"
            row.errors = str(e)
            row.finished_at = _utcnow()
            row.duration_seconds = int(time.time() - started)
            db.commit()
        finally:
            db.close()
        raise

    stats = result.get("stats") or {}

    db = SessionLocal()
    try:
        row = db.query(CommentRun).filter(CommentRun.id == run_id).first()
        row.status = "completed"
        row.posts_scraped = int(stats.get("posts_scraped_from_feed", 0))
        row.posts_new = int(stats.get("posts_new_and_inserted", 0))
        row.posts_selected = int(stats.get("posts_passed_filter", 0))
        row.comments_generated = int(stats.get("comments_generated", 0))
        row.comments_accepted = int(stats.get("comments_passed_critique", 0))
        row.errors = "\n".join(result.get("errors") or []) or None
        row.finished_at = _utcnow()
        row.duration_seconds = int(time.time() - started)
        db.commit()
    finally:
        db.close()

    return {"ran": True, "run_id": run_id, "stats": stats, "errors": result.get("errors") or []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LinkedIn comment scanner (discovery + drafts only)")
    parser.add_argument("--force", action="store_true", help="run even if not due")
    parser.add_argument("--max-posts", type=int, default=None, help="feed posts to scan")
    args = parser.parse_args(argv)

    try:
        outcome = run_cycle(max_posts=args.max_posts, force=args.force)
    except Exception as e:
        print(f"Comment cycle failed: {e}")
        return 1

    if not outcome.get("ran"):
        print(outcome.get("reason"))
        return 0

    stats = outcome["stats"]
    print(
        f"Run #{outcome['run_id']}: scanned {stats.get('posts_scraped_from_feed', 0)}, "
        f"new {stats.get('posts_new_and_inserted', 0)}, "
        f"relevant {stats.get('posts_passed_filter', 0)}, "
        f"drafted {stats.get('comments_passed_critique', 0)}"
    )
    for error in outcome.get("errors") or []:
        print(f"  ! {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
