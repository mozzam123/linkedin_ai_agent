"""
Streamlit approval queue for comment drafts.

Phase 3: the agent drafts comments, you approve or reject them. Nothing is
posted from this screen.
"""

import streamlit as st

from app.core.config import settings
from app.services.comment_poster import DAY_CAP, post_approved_comments, posting_status
from app.services.comment_scheduler import last_run, next_run_at
from app.services.comment_service import (
    approve_comment,
    pending_comments,
    reject_comment,
    run_comment_workflow,
)


def _score_badge(score):
    if score is None:
        return "—"
    return f"{score:.1f}/10"


def render_comment_queue():
    st.title("💬 Comment queue")
    st.caption(
        "The agent scans your feed, scores posts for relevance, and drafts a "
        "comment. **Nothing is posted from here** — approving just marks it ready."
    )

    # Scheduled scans (Phase 5) — discovery only, never posts
    previous = last_run()
    if previous:
        upcoming = next_run_at()
        st.caption(
            f"⏱️ Last scheduled scan: **{previous.started_at:%d %b %H:%M} UTC** — "
            f"{previous.posts_scraped} scanned, {previous.comments_accepted} drafted"
            + (f" · next due {upcoming:%d %b %H:%M} UTC" if upcoming else "")
        )

    st.markdown("---")

    col_a, col_b = st.columns([1, 2])
    with col_a:
        max_posts = st.number_input(
            "Posts to scan", min_value=1, max_value=20, value=5, step=1,
            help="Higher = more feed coverage, more LLM calls, slower.",
        )
    with col_b:
        st.markdown("&nbsp;")
        if st.button("🔍 Scan feed & draft comments", type="primary", use_container_width=True):
            with st.spinner("Scraping feed, scoring relevance, drafting comments…"):
                try:
                    result = run_comment_workflow(max_posts=int(max_posts))
                    st.session_state["comment_run"] = result
                except Exception as e:
                    st.session_state["comment_run"] = {"errors": [str(e)], "stats": {}}

    result = st.session_state.get("comment_run")
    if result:
        stats = result.get("stats") or {}
        st.success(
            f"Scanned {stats.get('posts_scraped_from_feed', 0)} posts · "
            f"{stats.get('posts_new_and_inserted', 0)} new · "
            f"{stats.get('posts_passed_filter', 0)} relevant · "
            f"{stats.get('comments_passed_critique', 0)} comment(s) drafted"
        )
        for error in result.get("errors") or []:
            st.warning(error)

    # ── Posting (Phase 4) ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🚀 Post approved comments")

    try:
        status = posting_status()
    except Exception as e:
        status = None
        st.error(f"Could not read posting status: {e}")

    if status:
        cooldown = (
            f"next allowed after {status['next_allowed_at']:%H:%M} UTC"
            if status["next_allowed_at"] and not status["can_post_now"]
            else "ready"
        )
        st.caption(
            f"Approved waiting: **{status['approved_waiting']}** · "
            f"Posted today: **{status['posted_today']}/{status['daily_cap']}** · {cooldown}"
        )

        if status.get("stale_approved"):
            st.warning(
                f"{status['stale_approved']} approved comment(s) belong to posts older than "
                f"{settings.MAX_COMMENT_AGE_HOURS}h. LinkedIn usually stops showing those posts, so they may not be "
                "findable — they will be marked expired when you try."
            )

        dry = st.checkbox(
            "Dry run — find the post and type the comment, but don't submit",
            value=False,
        )

        if st.button(
            "Post next approved comment",
            type="primary",
            disabled=not status["can_post_now"] or status["approved_waiting"] == 0,
        ):
            with st.spinner("Opening LinkedIn, locating the post, commenting…"):
                outcome = post_approved_comments(limit=1, dry_run=dry)
            if outcome.get("blocked_reason"):
                st.warning(outcome["blocked_reason"])
            for item in outcome.get("results") or []:
                if item.get("ok") and not item.get("dry_run"):
                    if item.get("confirmed"):
                        st.success(f"Comment #{item['comment_id']} posted and confirmed on the page.")
                    else:
                        st.warning(
                            f"Comment #{item['comment_id']}: submit was clicked but the comment "
                            "was not found on the page. Check LinkedIn before trusting it."
                        )
                elif item.get("ok"):
                    st.info(f"Dry run OK for comment #{item['comment_id']} — nothing submitted.")
                else:
                    st.error(f"Comment #{item['comment_id']} failed: {item.get('error')}")

            if outcome.get("expired"):
                st.warning(
                    f"{outcome['expired']} comment(s) were marked **expired** because the post "
                    "could no longer be found. Approve drafts and post them the same day."
                )

        st.caption(
            "Caps: 1 comment per run · 2h between comments · "
            f"{DAY_CAP} per day · 1 per creator per 48h. "
            "⚠️ Post the same day you approve — LinkedIn stops showing the post in "
            "your feed after that, and the agent can no longer find it."
        )

    st.markdown("---")
    items = pending_comments()

    if not items:
        st.info("No comments waiting for review. Run a scan above.")
        return

    st.markdown(f"### {len(items)} comment(s) waiting for review")

    for item in items:
        comment_id = item["comment_id"]
        author = item["author_name"] or "Unknown author"
        preview = (item["comment_text"] or "").strip().replace("\n", " ")[:70]

        with st.expander(f"{author} — {preview}…", expanded=False):
            st.markdown(f"**Original post** · score {_score_badge(item['self_score'])}")
            st.text_area(
                "post_text", value=item["post_text"] or "", height=140,
                disabled=True, label_visibility="collapsed",
                key=f"post_{comment_id}",
            )

            edited = st.text_area(
                "Your comment", value=item["comment_text"] or "", height=110,
                key=f"comment_{comment_id}",
            )

            if item["self_critique"]:
                st.caption(f"Self-critique: {item['self_critique']}")

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("✅ Approve", key=f"approve_{comment_id}", use_container_width=True):
                    approve_comment(comment_id, edited)
                    st.rerun()
            with col2:
                if st.button("✖ Reject", key=f"reject_{comment_id}", use_container_width=True):
                    reject_comment(comment_id)
                    st.rerun()
            with col3:
                # Synthetic keys (no permalink available on the new feed) are
                # not openable, so only real URLs get a link button.
                if item["post_url"] and item["post_url"].startswith("http"):
                    st.link_button("Open post on LinkedIn", item["post_url"], use_container_width=True)
