import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.rewrite_prompts import REWRITE_PROMPT


def rewrite_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        llm       = get_llm()
        post_goal = state.get("post_goal") or "IMPRESSIONS"

        # Generate targeted advice based on critique scores
        critique_scores = state.get("critique_scores") or {}
        advice_lines = []
        if critique_scores:
            hook = critique_scores.get("hook", 5.0)
            if hook < 6:
                advice_lines.append(f"- Hook score: {hook}/10 — Strengthen the opening to create immediate curiosity or contradiction.")
            entry = critique_scores.get("entry_point", 5.0)
            if entry < 6:
                advice_lines.append(f"- Entry point score: {entry}/10 — Ground the post in a specific moment or shared tension before presenting the insight.")
            specificity = critique_scores.get("specificity", 5.0)
            if specificity < 6:
                advice_lines.append(f"- Specificity score: {specificity}/10 — Add a concrete detail like a number, timeline, or specific system name.")
            human_feel = critique_scores.get("human_feel", 5.0)
            if human_feel < 6:
                advice_lines.append(f"- Human feel score: {human_feel}/10 — Make the post more conversational and relatable; avoid sounding overly formal or theoretical.")
            goal_alignment = critique_scores.get("goal_alignment", 5.0)
            if goal_alignment < 6:
                advice_lines.append(f"- Goal alignment score: {goal_alignment}/10 — Ensure the post structure matches the selected goal ({post_goal}).")
            dwell_time = critique_scores.get("dwell_time", 5.0)
            if dwell_time < 6:
                advice_lines.append(f"- Dwell time score: {dwell_time}/10 — Increase engagement by adding a named pattern, surprising insight, or open-ended question.")
        if not advice_lines:
            advice_lines.append("- All scores are satisfactory; focus on the priority fix and overall clarity.")
        targeted_advice = "\n".join(advice_lines)

        prompt = REWRITE_PROMPT.format(
            post=state["generated_post"],
            critique=state["critique"],
            targeted_advice=targeted_advice,
            post_goal=post_goal,
        )

        response = llm.invoke(prompt)

        state["generated_post"]  = response.content
        state["final_post"]      = response.content  # Always keep final_post in sync
        state["iteration_count"] += 1

    except Exception as e:
        state["errors"].append(f"Error in rewrite_node: {str(e)}")
        state["status"] = "failed"

    return state