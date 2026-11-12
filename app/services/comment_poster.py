"""
Phase 4: post approved comments to LinkedIn.

This is the irreversible step, so it is conservative by design:
  - only comments with status='approved' are considered
  - at most one comment per run (MIN_HOURS_BETWEEN_COMMENTS = 2h between any two)
  - stops at MAX_COMMENTS_PER_DAY for the day
  - skips a creator already commented on within 48h
  - LINKEDIN_DRY_RUN=1 finds the post and types the comment but never submits
  - a failure is recorded on the row and does not consume the daily budget

Every attempt updates the DB, so nothing is ever posted twice.
"""

from datetime import datetime, timedelta

from app.automation.actions import (
    FEED_URL,
    ActionError,
    browser_session,
    comment_on_post,
    comment_editor_cleared,
    comment_visible,
    ensure_logged_in,
    goto,
    is_dry_run,
)
from app.core.config import settings
from app.db.models.creator_profile_model import CreatorProfile
from app.db.models.discovered_post_model import DiscoveredPost
from app.db.models.generated_comment_model import GeneratedComment
from app.db.session import SessionLocal

DAY_CAP = settings.MAX_COMMENTS_PER_DAY
CREATOR_COOLDOWN = timedelta(hours=settings.MAX_COMMENTS_PER_CREATOR_PER_48H * 48)
GAP = timedelta(hours=settings.MIN_HOURS_BETWEEN_COMMENTS)


def _utcnow() -> datetime:
    return datetime.utcnow()


def posting_status() -> dict:
    """What the caps allow right now."""
    db = SessionLocal()
    try:
        today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        posted_today = (
            db.query(GeneratedComment)
            .filter(
                GeneratedComment.status.in_(("published", "published_unverified")),
                GeneratedComment.published_at >= today_start,
            )
            .count()
        )
        last = (
            db.query(GeneratedComment.published_at)
            .filter(GeneratedComment.status.in_(("published", "published_unverified")))
            .order_by(GeneratedComment.published_at.desc())
            .first()
        )
        last_at = last[0] if last else None
        next_allowed = (last_at + GAP) if last_at else None

        approved = db.query(GeneratedComment).filter(GeneratedComment.status == "approved").count()

        # Stale = the post is older than the window in which it can be found
        stale_cutoff = _utcnow() - timedelta(hours=settings.MAX_COMMENT_AGE_HOURS)
        stale = (
            db.query(GeneratedComment)
            .join(DiscoveredPost, GeneratedComment.discovered_post_id == DiscoveredPost.id)
            .filter(
                GeneratedComment.status == "approved",
                DiscoveredPost.scraped_at < stale_cutoff,
            )
            .count()
        )

        return {
            "approved_waiting": approved,
            "stale_approved": stale,
            "posted_today": posted_today,
            "daily_cap": DAY_CAP,
            "remaining_today": max(DAY_CAP - posted_today, 0),
            "last_posted_at": last_at,
            "next_allowed_at": next_allowed,
            "can_post_now": (
                posted_today < DAY_CAP and (next_allowed is None or _utcnow() >= next_allowed)
            ),
        }
    finally:
        db.close()


def _touch_creator(db, author_url: str | None, author_name: str | None) -> None:
    """Record the interaction so the 48h creator cooldown applies."""
    if not author_url:
        return
    creator = db.query(CreatorProfile).filter(CreatorProfile.linkedin_url == author_url).first()
    if creator is None:
        creator = CreatorProfile(linkedin_url=author_url, name=author_name)
        db.add(creator)
    creator.last_commented_at = _utcnow()
    creator.total_comments_made = (creator.total_comments_made or 0) + 1


def post_approved_comments(limit: int | None = None, dry_run: bool | None = None) -> dict:
    """
    Post approved comments, one per run.

    Returns {"posted": n, "results": [...], "blocked_reason": str|None}.
    """
    dry = is_dry_run() if dry_run is None else dry_run
    status = posting_status()

    if status["posted_today"] >= DAY_CAP:
        return {"posted": 0, "results": [], "blocked_reason": f"Daily cap reached ({DAY_CAP})."}
    if status["next_allowed_at"] and _utcnow() < status["next_allowed_at"]:
        return {
            "posted": 0,
            "results": [],
            "blocked_reason": (
                f"Cooling down until {status['next_allowed_at']:%H:%M} UTC "
                f"({settings.MIN_HOURS_BETWEEN_COMMENTS}h between comments)."
            ),
        }

    db = SessionLocal()
    try:
        rows = (
            db.query(GeneratedComment, DiscoveredPost)
            .join(DiscoveredPost, GeneratedComment.discovered_post_id == DiscoveredPost.id)
            .filter(GeneratedComment.status == "approved")
            .all()
        )

        # Age is a warning, not a verdict: only the actual locate attempt can
        # tell whether the post is still reachable. Freshest posts are tried
        # first because they are the most likely to be found.
        cutoff = _utcnow() - timedelta(hours=settings.MAX_COMMENT_AGE_HOURS)
        queue = []
        stale = 0
        for comment, post in rows:
            is_stale = bool(post.scraped_at and post.scraped_at < cutoff)
            stale += int(is_stale)
            queue.append(
                {
                    "comment_id": comment.id,
                    "comment_text": comment.comment_text,
                    "post_text": post.post_text,
                    "post_url": post.post_url,
                    "author_name": post.author_name,
                    "author_url": post.author_linkedin_url,
                    "scraped_at": post.scraped_at,
                    "stale": is_stale,
                }
            )
        queue.sort(key=lambda item: (item["stale"], -(item["scraped_at"].timestamp() if item["scraped_at"] else 0)))
    finally:
        db.close()

    # Apply the per-run limit only after ordering, so the freshest goes first
    queue = queue[: (limit or 1)]

    if not queue:
        return {
            "posted": 0,
            "results": [],
            "blocked_reason": (
                "No approved comments waiting — approve a draft in the queue first."
            ),
        }

    results: list[dict] = []
    posted = 0

    with browser_session(headless=True) as page:
        goto(page, FEED_URL)
        ensure_logged_in(page)

        for item in queue:
            try:
                submitted = comment_on_post(
                    page,
                    post_text=item["post_text"],
                    comment_text=item["comment_text"],
                    author_name=item["author_name"],
                    post_url=item["post_url"],
                    author_url=item["author_url"],
                    dry_run=dry,
                )
            except ActionError as e:
                db = SessionLocal()
                try:
                    row = db.query(GeneratedComment).filter(
                        GeneratedComment.id == item["comment_id"]
                    ).first()
                    if row:
                        row.publish_error = str(e)
                        # A post that can no longer be located will never succeed:
                        # take it out of the approved pool instead of retrying forever.
                        if "could not be located" in str(e) or "not in the feed" in str(e):
                            row.status = "expired"
                        db.commit()
                finally:
                    db.close()
                results.append({"comment_id": item["comment_id"], "ok": False, "error": str(e)})
                continue

            # A click is not proof: confirm the comment is actually on the page.
            # Comments often sit under a collapsed "Load more comments", so try
            # expanding once before declaring it unverified.
            confirmed = bool(submitted and comment_visible(page, item["comment_text"]))
            if submitted and not confirmed:
                for label in ("Load more comments", "Show previous comments", "View more comments"):
                    try:
                        more = page.get_by_text(label, exact=False)
                        if more.count() and more.first.is_visible():
                            more.first.click()
                            page.wait_for_timeout(2500)
                            break
                    except Exception:
                        continue
                confirmed = comment_visible(page, item["comment_text"])

            # Second signal: LinkedIn clears the composer when it accepts the
            # comment. Either signal is enough to treat it as posted.
            if submitted and not confirmed:
                confirmed = comment_editor_cleared(page)

            db = SessionLocal()
            try:
                row = db.query(GeneratedComment).filter(
                    GeneratedComment.id == item["comment_id"]
                ).first()
                if submitted and row:
                    row.status = "published" if confirmed else "published_unverified"
                    row.published_at = _utcnow()
                    row.publish_error = (
                        None if confirmed
                        else "Submit clicked, but the comment was not found on the page — verify manually"
                    )
                    _touch_creator(db, item["author_url"], item["author_name"])
                db.commit()
            finally:
                db.close()

            results.append(
                {"comment_id": item["comment_id"], "ok": True, "dry_run": dry, "confirmed": confirmed}
            )
            if submitted:
                posted += 1
                break  # one per run, then the 2h gap applies

    expired_ids = [r["comment_id"] for r in results if not r.get("ok") and "located" in (r.get("error") or "")]

    return {
        "posted": posted,
        "results": results,
        "blocked_reason": None,
        "dry_run": dry,
        "expired": len(expired_ids),
        "stale_in_queue": stale,
    }
