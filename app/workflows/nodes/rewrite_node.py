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

        prompt = REWRITE_PROMPT.format(
            post=state["generated_post"],
            critique=state["critique"],
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