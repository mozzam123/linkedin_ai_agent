"""
Streamlit approval queue for comment drafts.

Phase 3: the agent drafts comments, you approve or reject them. Nothing is
posted from this screen.
"""

import streamlit as st

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
