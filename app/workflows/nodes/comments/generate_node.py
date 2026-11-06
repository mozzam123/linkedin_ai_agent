"""
generate_node.py
────────────────
Third node in the comment workflow. Turns the posts that survived relevance
scoring into draft comments, self-scores each one, and stores the good ones
in `generated_comment` with status='pending_approval'.

Nothing is posted here. Phase 3 stops at the approval queue; posting is a
separate, later step.

Cost control: at most MAX_COMMENTS_TO_POST_PER_RUN posts are turned into
comments per run, and each comment gets at most two attempts.
"""

import json
import re
import time

from app.core.config import settings
from app.db.models.discovered_post_model import DiscoveredPost
from app.db.models.generated_comment_model import GeneratedComment
from app.db.session import SessionLocal
from app.prompts.comment_prompts import COMMENT_CRITIQUE_PROMPT, COMMENT_GENERATION_PROMPT
from app.services.llm_service import get_llm
from app.workflows.state.comment_state import CommentWorkflowState

MAX_ATTEMPTS = 2  # first try + one retry if the self-score is too low


def _extract_json(raw: str) -> dict | None:
    """Models sometimes wrap JSON in prose or fences. Pull out the object."""
    if not raw:
        return None
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def _score_comment(llm, post_text: str, comment: str) -> tuple[float, str]:
    prompt = COMMENT_CRITIQUE_PROMPT.format(post_text=post_text, comment=comment)
    try:
        parsed = _extract_json(llm.invoke(prompt).content or "")
    except Exception:
        parsed = None
    if not parsed:
        return 5.0, "Could not parse self-critique response"
    try:
        score = float(parsed.get("score", 5.0))
    except (TypeError, ValueError):
        score = 5.0
    return score, str(parsed.get("critique", ""))


def _generate_comment(llm, post_text: str) -> dict | None:
    voice = "\n".join(f"- {v}" for v in settings.VOICE_EXAMPLES)
    prompt = COMMENT_GENERATION_PROMPT.format(voice_examples=voice, post_text=post_text)
    try:
        parsed = _extract_json(llm.invoke(prompt).content or "")
    except Exception:
        return None
    if not parsed or not str(parsed.get("comment", "")).strip():
        return None
    return parsed


def generate_node(state: CommentWorkflowState) -> dict:
    start = time.time()
    run_errors = list(state.get("run_errors", []))
    stats = dict(state.get("stats") or {})
    trace = state["trace"]
    selected = state.get("selected_posts") or []

    if not selected:
        trace.log_step("generate_node", {"posts_in": 0}, {"comments": 0}, time.time() - start)
        return {
            "generated_comments": [],
            "approved_comments": [],
            "status": "comments_generated",
            "run_errors": run_errors,
            "stats": stats,
            "trace": trace,
        }

    # One LLM client for the whole node: same settings, no reconnect cost.
    llm = get_llm(temperature=0.7, max_tokens=400, reasoning_effort="low")
    db = SessionLocal()

    generated: list[dict] = []
    accepted: list[dict] = []

    try:
        budget = settings.MAX_COMMENTS_TO_POST_PER_RUN

        for post in selected[:budget]:
            post_text = post.get("post_text", "")
            post_url = post.get("post_url", "")
            db_id = post.get("db_id")
            if not post_text or not db_id:
                run_errors.append(f"Skipping post without text/db_id: {post_url}")
                continue

            best = None
            attempts = 0
            for attempt in range(1, MAX_ATTEMPTS + 1):
                attempts = attempt
                draft = _generate_comment(llm, post_text)
                if not draft:
                    continue

                comment_text = str(draft.get("comment", "")).strip()
                score, critique = _score_comment(llm, post_text, comment_text)
                candidate = {
                    "post_url": post_url,
                    "db_id": db_id,
                    "comment_text": comment_text,
                    "ending": str(draft.get("ending", "closed")),
                    "anchor": str(draft.get("anchor", "")),
                    "self_score": score,
                    "self_critique": critique,
                    "generation_attempt": attempt,
                }
                if best is None or score > best["self_score"]:
                    best = candidate
                if score >= settings.COMMENT_SELF_SCORE_THRESHOLD:
                    break

            if best is None:
                run_errors.append(f"Comment generation failed for {post_url}")
                continue

            passed = best["self_score"] >= settings.COMMENT_SELF_SCORE_THRESHOLD
            status = "pending_approval" if passed else "rejected"
            rejection = None if passed else (
                f"Self-score {best['self_score']:.1f} below "
                f"{settings.COMMENT_SELF_SCORE_THRESHOLD}: {best['self_critique']}"
            )

            try:
                row = GeneratedComment(
                    discovered_post_id=db_id,
                    comment_text=best["comment_text"],
                    comment_length=len(best["comment_text"]),
                    self_score=best["self_score"],
                    self_critique=best["self_critique"],
                    is_generic=not passed,
                    generation_attempt=best["generation_attempt"],
                    status=status,
                    rejection_reason=rejection,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                best["comment_id"] = row.id

                post_row = db.query(DiscoveredPost).filter(DiscoveredPost.id == db_id).first()
                if post_row:
                    post_row.status = "comment_generated"
                    db.commit()

            except Exception as e:
                db.rollback()
                run_errors.append(f"DB write failed for {post_url}: {e}")
                continue

            generated.append(best)
            if passed:
                accepted.append(best)

    finally:
        db.close()

    stats["comments_generated"] = len(generated)
    stats["comments_passed_critique"] = len(accepted)
    stats["comments_attempts"] = sum(c["generation_attempt"] for c in generated)

    trace.log_step(
        "generate_node",
        {"posts_in": len(selected), "budget": settings.MAX_COMMENTS_TO_POST_PER_RUN},
        {"generated": len(generated), "accepted": len(accepted)},
        time.time() - start,
    )

    return {
        "generated_comments": generated,
        "approved_comments": accepted,
        "status": "comments_generated",
        "run_errors": run_errors,
        "stats": stats,
        "trace": trace,
    }
