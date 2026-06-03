import json
import re
import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.critique_prompts import CRITIQUE_PROMPT


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
        llm       = get_llm(temperature=0.2)
        post      = state.get("generated_post") or ""
        post_goal = state.get("post_goal") or "IMPRESSIONS"

        if not post:
            raise ValueError("generated_post is empty — draft_node may have failed")

        prompt   = CRITIQUE_PROMPT.format(post=post, post_goal=post_goal)
        response = llm.invoke(prompt)

        parsed  = _parse_critique(response.content)
        overall = parsed.get("overall_score", 5.0)

        state["score"] = float(overall) if overall is not None else 5.0
        state["critique"] = (
            f"PRIORITY FIX: {parsed.get('priority_fix', '')}\n\n"
            f"Hook: {parsed.get('hook')}/10 | "
            f"Entry: {parsed.get('entry_point')}/10 | "
            f"Specificity: {parsed.get('specificity')}/10 | "
            f"Human Feel: {parsed.get('human_feel')}/10 | "
            f"Goal Alignment: {parsed.get('goal_alignment')}/10 | "
            f"Dwell Time: {parsed.get('dwell_time')}/10"
        )

    except Exception as e:
        state["errors"].append(f"Error in critique_node: {str(e)}")
        state["status"] = "failed"
        state["score"]  = float(state.get("score") or 0.0)

    return state