"""
discovery_node.py
─────────────────
WHAT THIS NODE DOES
───────────────────
This is the first node in the comment workflow graph. Its only job is to
collect raw post data from the LinkedIn feed and figure out which posts
are genuinely new (not seen in any previous run).

Concretely it does four things:
  1. Calls the scraper to collect up to MAX_POSTS_TO_SCRAPE_PER_RUN posts
     from the live LinkedIn feed.
  2. Loads every post URL already in the discovered_posts table from the DB
     so it can deduplicate — a post the system has already seen (regardless
     of what happened to it) is never processed again.
  3. Filters out posts from creators who have is_blocked=True in the
     creator_profiles table — a manual block flag you can set to permanently
     exclude certain creators.
  4. Inserts the remaining new posts into discovered_posts with
     status='scraped', then returns them in state so the next node
     (relevance_node) can score them.

HOW IT CONNECTS TO THE REST OF THE GRAPH
─────────────────────────────────────────
Input  state keys read  : (none — this is the entry node)
Output state keys set   : scraped_posts, status, run_errors, stats, trace

The graph's conditional edge after this node checks state["status"]:
  - "failed"        → END  (session expired or total scraper crash)
  - "discovery_done" → relevance_node

If scraped_posts comes back empty (feed was fine but all posts were already
seen), the graph still routes to relevance_node — that node will simply
return an empty selected_posts and the graph ends gracefully at the
scoring conditional edge.
"""

import time

from app.workflows.state.comment_state import CommentWorkflowState
from app.automation.linkedin_scraper import scrape_linkedin_feed, SessionExpiredError, ScraperError
from app.db.session import SessionLocal
from app.db.models.discovered_post_model import DiscoveredPost
from app.db.models.creator_profile_model import CreatorProfile
from app.core.config import settings


def discovery_node(state: CommentWorkflowState) -> dict:
    start      = time.time()
    run_errors = list(state.get("run_errors", []))
    stats      = dict(state.get("stats") or {})
    trace      = state["trace"]

    # ── 1. Run the scraper ─────────────────────────────────────────────────
    try:
        raw_posts = scrape_linkedin_feed(
            max_posts=settings.MAX_POSTS_TO_SCRAPE_PER_RUN
        )
    except SessionExpiredError as e:
        # Fatal: no point continuing without an authenticated session.
        trace.log_step("discovery_node", {}, {"error": str(e)}, time.time() - start)
        return {
            "scraped_posts": [],
            "status":        "failed",
            "run_errors":    run_errors + [f"Session expired: {e}"],
            "stats":         stats,
            "trace":         trace,
        }
    except ScraperError as e:
        # Fatal: scraper crashed before collecting anything.
        trace.log_step("discovery_node", {}, {"error": str(e)}, time.time() - start)
        return {
            "scraped_posts": [],
            "status":        "failed",
            "run_errors":    run_errors + [f"Scraper error: {e}"],
            "stats":         stats,
            "trace":         trace,
        }

    # ── 2. Load already-seen URLs from DB ──────────────────────────────────
    # Any post that exists in the table (in any status) is considered seen.
    # This prevents re-processing a post that was previously skipped,
    # already commented on, or is mid-pipeline from an earlier run.
    db = SessionLocal()
    try:
        seen_urls = {
            row.post_url
            for row in db.query(DiscoveredPost.post_url).all()
        }

        # ── 3. Load blocked creator URLs ───────────────────────────────────
        blocked_creator_urls = {
            row.linkedin_url
            for row in db.query(CreatorProfile.linkedin_url)
            .filter(CreatorProfile.is_blocked == True)  # noqa: E712
            .all()
        }

        # ── 4. Filter: new posts only, no blocked creators ─────────────────
        new_posts   = []
        skip_count  = 0

        for post in raw_posts:
            post_url    = post.get("post_url", "")
            author_url  = post.get("author_linkedin_url", "")

            if post_url in seen_urls:
                skip_count += 1
                continue

            if author_url and author_url in blocked_creator_urls:
                run_errors.append(
                    f"Skipped post from blocked creator: {post.get('author_name', author_url)}"
                )
                skip_count += 1
                continue

            new_posts.append(post)

        # ── 5. Insert new posts into discovered_posts ──────────────────────
        # Each post gets its own DB row with status='scraped'.
        # On the rare chance a duplicate slips through the in-memory filter
        # (e.g. two concurrent runs), the unique constraint on post_url will
        # fire — we catch IntegrityError per row and continue rather than
        # letting one duplicate crash the whole batch.
        from sqlalchemy.exc import IntegrityError

        inserted = 0
        for post in new_posts:
            try:
                row = DiscoveredPost(
                    post_url            = post["post_url"],
                    author_name         = post.get("author_name"),
                    author_linkedin_url = post.get("author_linkedin_url"),
                    post_text           = post["post_text"],
                    post_type           = post.get("post_type", "text"),
                    status              = "scraped",
                )
                db.add(row)
                db.commit()
                db.refresh(row)

                # Attach the DB-assigned id back onto the dict so later
                # nodes can use it as a foreign key without re-querying.
                post["db_id"] = row.id
                inserted += 1

            except IntegrityError:
                db.rollback()
                run_errors.append(
                    f"Duplicate post skipped (race condition): {post['post_url']}"
                )

    finally:
        db.close()

    # ── 6. Build stats and trace ───────────────────────────────────────────
    stats["posts_scraped_from_feed"] = len(raw_posts)
    stats["posts_already_seen"]      = skip_count
    stats["posts_new_and_inserted"]  = inserted

    trace.log_step(
        "discovery_node",
        {"max_posts_requested": settings.MAX_POSTS_TO_SCRAPE_PER_RUN},
        {
            "scraped_from_feed": len(raw_posts),
            "new_inserted":      inserted,
            "skipped":           skip_count,
        },
        time.time() - start,
    )

    return {
        "scraped_posts": new_posts,   # only the new ones, with db_id attached
        "status":        "discovery_done",
        "run_errors":    run_errors,
        "stats":         stats,
        "trace":         trace,
    }