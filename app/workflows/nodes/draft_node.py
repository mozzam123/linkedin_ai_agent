import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT
from app.utils.style_loader import load_style_examples


def draft_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        style_examples = load_style_examples()
        llm            = get_llm()

        # post_goal tells the draft exactly what to optimise for
        post_goal = state.get("post_goal") or "IMPRESSIONS"

        prompt = DRAFT_GENERATION_PROMPT.format(
            topic=state["topic"],
            research=state["research_notes"],
            style_examples=style_examples,
            post_goal=post_goal,
        )

        response               = llm.invoke(prompt)
        state["generated_post"] = response.content
        state["final_post"]     = response.content  # Keep in sync from first draft

    except Exception as e:
        state["errors"].append(f"Error in draft_node: {str(e)}")
        state["status"] = "failed"

    return state