"""
relevance_node.py
─────────────────
WHAT THIS NODE DOES
───────────────────
This is the second node. It takes every new post from discovery_node and
decides which ones are actually worth commenting on.

It does this in two layers:

Layer 1 — Hard filters (no LLM call, instant, cheap):
  These rules eliminate obvious non-candidates before spending any tokens:
  • Creator cooldown  : if we've commented on this creator in the last 48 h,
                        skip regardless of how good the post is.
  • Already commented : if a GeneratedComment row exists for this
                        discovered_post_id (status not 'failed'), skip.

Layer 2 — LLM relevance scoring (one call per post that passes layer 1):
  A structured prompt asks the LLM to score the post 0–10 against your
  niche topics and return JSON with: score, reason, skip_reason.
  Posts scoring below RELEVANCE_SCORE_THRESHOLD are skipped.

After both layers, the node updates each discovered_posts row in the DB:
  • Passed  → status='scored',  relevance_score and relevance_reason saved
  • Skipped → status='skipped', skip_reason saved

HOW IT CONNECTS TO THE REST OF THE GRAPH
─────────────────────────────────────────
Input  state keys read  : scraped_posts, run_errors, stats, trace
Output state keys set   : scored_posts, selected_posts, status,
                          run_errors, stats, trace

The graph's conditional edge after this node checks selected_posts:
  - empty list → END  (nothing relevant, no point generating comments)
  - non-empty  → comment_node
"""

import json
import time

from app.workflows.state.comment_state import CommentWorkflowState
from app.services.llm_service import get_llm
from app.db.session import SessionLocal
from app.db.models.discovered_post_model import DiscoveredPost
from app.db.models.generated_comment_model import GeneratedComment
from app.db.models.creator_profile_model import CreatorProfile
from app.core.config import settings


# ── Relevance scoring prompt ───────────────────────────────────────────────────
# Lives here (not in a separate prompts file) because it is tightly coupled
# to the config values and only used by this one node.

def _build_relevance_prompt(post_text: str) -> str:
    niche   = ", ".join(settings.NICHE_TOPICS)
    signals = ", ".join(settings.NICHE_SKIP_SIGNALS)

    return f"""You are a relevance classifier for a LinkedIn engagement system.

Your job: score the post below on how relevant it is to these topics:
{niche}

Give a score of 0 if the post is clearly about any of these unrelated areas:
{signals}

POST TEXT:
\"\"\"{post_text}\"\"\"

Respond with ONLY valid JSON — no markdown, no explanation, nothing else.
Schema:
{{
  "score": <float 0.0 to 10.0>,
  "reason": "<one sentence explaining the score>",
  "skip_reason": "<one sentence why to skip, or null if score is acceptable>"
}}"""


def _score_post_with_llm(post_text: str, llm) -> dict:
    """
    Call the LLM to score one post. Returns a dict with score, reason,
    skip_reason. On any parse failure, returns score=0 with a note.
    """
    prompt   = _build_relevance_prompt(post_text)
    response = llm.invoke(prompt)
    raw      = (response.content or "").strip()

    try:
        # Strip markdown code fences if the LLM adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {
            "score":       0.0,
            "reason":      "LLM returned unparseable response",
            "skip_reason": "Could not parse LLM relevance response",
        }


def relevance_node(state: CommentWorkflowState) -> dict:
    start        = time.time()
    run_errors   = list(state.get("run_errors", []))
    stats        = dict(state.get("stats") or {})
    trace        = state["trace"]
    scraped_posts = state.get("scraped_posts") or []

    if not scraped_posts:
        # Nothing to score — pass through gracefully
        trace.log_step("relevance_node", {"posts_in": 0}, {"posts_selected": 0}, time.time() - start)
        return {
            "scored_posts":   [],
            "selected_posts": [],
            "status":         "scoring_done",
            "run_errors":     run_errors,
            "stats":          stats,
            "trace":          trace,
        }

    llm        = get_llm()
    db         = SessionLocal()
    scored     = []   # all posts with scores attached (including skipped)
    selected   = []   # posts that passed both filter layers

    try:
        # Pre-load creator cooldown data in one query rather than N queries.
        # Maps author_linkedin_url → last_commented_at datetime (or None).
        from datetime import datetime, timedelta

        creator_rows = db.query(
            CreatorProfile.linkedin_url,
            CreatorProfile.last_commented_at,
            CreatorProfile.is_blocked,
        ).all()
        creator_map = {
            row.linkedin_url: row
            for row in creator_rows
        }

        cooldown_cutoff = datetime.utcnow() - timedelta(hours=48)

        for post in scraped_posts:
            post_url   = post.get("post_url", "")
            author_url = post.get("author_linkedin_url", "")
            db_id      = post.get("db_id")    # set by discovery_node
            post_copy  = dict(post)           # don't mutate the original

            skip_reason = None

            # ── Layer 1a: Creator cooldown check ──────────────────────────
            if author_url and author_url in creator_map:
                creator = creator_map[author_url]
                if creator.is_blocked:
                    skip_reason = "Creator is manually blocked"
                elif (
                    creator.last_commented_at
                    and creator.last_commented_at > cooldown_cutoff
                ):
                    skip_reason = (
                        f"Creator cooldown active — last commented "
                        f"{creator.last_commented_at.strftime('%Y-%m-%d %H:%M')} UTC"
                    )

            # ── Layer 1b: Already have a comment for this post ─────────────
            if not skip_reason and db_id:
                existing = (
                    db.query(GeneratedComment)
                    .filter(
                        GeneratedComment.discovered_post_id == db_id,
                        GeneratedComment.status != "failed",
                    )
                    .first()
                )
                if existing:
                    skip_reason = "A comment for this post already exists in the system"

            # ── Layer 2: LLM relevance scoring (only if not skipped) ───────
            if skip_reason:
                post_copy["relevance_score"]  = 0.0
                post_copy["relevance_reason"] = skip_reason
                post_copy["skip_reason"]      = skip_reason
                final_status                  = "skipped"
            else:
                try:
                    result = _score_post_with_llm(post["post_text"], llm)
                except Exception as e:
                    run_errors.append(f"LLM scoring failed for {post_url}: {e}")
                    result = {
                        "score":       0.0,
                        "reason":      f"LLM call failed: {e}",
                        "skip_reason": "LLM scoring error",
                    }

                score       = float(result.get("score", 0.0))
                reason      = result.get("reason", "")
                llm_skip    = result.get("skip_reason")    # None means "no skip"

                post_copy["relevance_score"]  = score
                post_copy["relevance_reason"] = reason

                if score < settings.RELEVANCE_SCORE_THRESHOLD or llm_skip:
                    skip_reason = llm_skip or f"Score {score:.1f} below threshold {settings.RELEVANCE_SCORE_THRESHOLD}"
                    post_copy["skip_reason"] = skip_reason
                    final_status             = "skipped"
                else:
                    post_copy["skip_reason"] = None
                    final_status             = "scored"
                    selected.append(post_copy)

            scored.append(post_copy)

            # ── Update DB row with scoring results ─────────────────────────
            if db_id:
                try:
                    db_row = db.query(DiscoveredPost).filter(DiscoveredPost.id == db_id).first()
                    if db_row:
                        db_row.relevance_score  = post_copy.get("relevance_score")
                        db_row.relevance_reason = post_copy.get("relevance_reason")
                        db_row.skip_reason      = post_copy.get("skip_reason")
                        db_row.status           = final_status
                        db.commit()
                except Exception as e:
                    db.rollback()
                    run_errors.append(f"DB update failed for post {db_id}: {e}")

    finally:
        db.close()

    # ── Stats and trace ────────────────────────────────────────────────────
    stats["posts_scored"]          = len(scored)
    stats["posts_passed_filter"]   = len(selected)
    stats["posts_skipped"]         = len(scored) - len(selected)

    trace.log_step(
        "relevance_node",
        {"posts_in": len(scraped_posts)},
        {
            "scored":   len(scored),
            "selected": len(selected),
            "skipped":  len(scored) - len(selected),
        },
        time.time() - start,
    )

    return {
        "scored_posts":   scored,
        "selected_posts": selected,
        "status":         "scoring_done",
        "run_errors":     run_errors,
        "stats":          stats,
        "trace":          trace,
    }