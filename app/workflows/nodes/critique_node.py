import json, re
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.critique_prompts import CRITIQUE_PROMPT


def _to_score(value, fallback: float = 5.0) -> float:
    """Models sometimes answer with words ("High") or strings ("7"). Normalise."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("/10", "").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return fallback
    return fallback


def _parse_critique(raw: str) -> dict:
    """
    Parse critique JSON from LLM response.
    Handles three formats:
    1. Raw JSON
    2. ```json ... ``` fenced
    3. ``` ... ``` fenced without language tag
    """
    default = {
        "hook": 5.0,
        "entry_point": 5.0,
        "specificity": 5.0,
        "human_feel": 5.0,
        "goal_alignment": 5.0,
        "dwell_time": 5.0,
        "priority_fix": "Rewrite for stronger hook and add one specific concrete detail",
        "overall_score": 5.0,
    }

    try:
        clean = raw.strip()

        # Extract content from fenced block if present
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", clean)
        if fenced:
            clean = fenced.group(1).strip()

        # Find the JSON object even if there's surrounding text
        json_match = re.search(r"\{[\s\S]*\}", clean)
        if json_match:
            clean = json_match.group(0)

        parsed = json.loads(clean)

        # Validate all expected keys exist, fill missing with defaults
        for key, val in default.items():
            if key not in parsed:
                parsed[key] = val

        return parsed

    except Exception as e:
        return default


def critique_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    # Always initialise score so route_after_critique never gets None
    state["score"] = float(state.get("score") or 0.0)

    try:
        llm = get_llm(temperature=0.2, max_tokens=700, reasoning_effort="low")
        post = state.get("generated_post") or ""
        post_goal = state.get("post_goal") or "IMPRESSIONS"

        if not post.strip():
            raise ValueError("generated_post is empty — draft_node may have failed")

        prompt = CRITIQUE_PROMPT.format(post=post, post_goal=post_goal)
        response = llm.invoke(prompt)

        parsed = _parse_critique(response.content or "")
        overall = _to_score(parsed.get("overall_score"), 5.0)

        state["score"] = overall
        subscores = {
            key: _to_score(parsed.get(key), 5.0)
            for key in ("hook", "entry_point", "specificity", "human_feel",
                        "goal_alignment", "dwell_time")
        }
        state["critique"] = (
            f"PRIORITY FIX: {parsed.get('priority_fix', '')}\n\n"
            f"Hook: {subscores['hook']}/10 | "
            f"Entry: {subscores['entry_point']}/10 | "
            f"Specificity: {subscores['specificity']}/10 | "
            f"Human Feel: {subscores['human_feel']}/10 | "
            f"Goal Alignment: {subscores['goal_alignment']}/10 | "
            f"Dwell Time: {subscores['dwell_time']}/10"
        )
        # Store sub-scores for targeted rewrites
        state["critique_scores"] = subscores

        # Keep the highest-scoring version so a rewrite can never degrade the post
        best_score = state.get("best_score")
        if best_score is None or overall > float(best_score):
            state["best_score"] = overall
            state["best_post"]  = post

    except Exception as e:
        state["errors"].append(f"Error in critique_node: {str(e)}")
        state["status"] = "failed"
        state["score"] = float(state.get("score") or 0.0)
        # Provide default scores on error
        state["critique_scores"] = {
            "hook": 5.0,
            "entry_point": 5.0,
            "specificity": 5.0,
            "human_feel": 5.0,
            "goal_alignment": 5.0,
            "dwell_time": 5.0,
        }

    return state
