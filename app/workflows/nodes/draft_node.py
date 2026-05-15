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
        llm = get_llm()

        prompt = DRAFT_GENERATION_PROMPT.format(
            topic=state["topic"],
            research=state["research_notes"],
            style_examples=style_examples
        )

        response = llm.invoke(prompt)
        state["generated_post"] = response.content
        
    except Exception as e:
        state["errors"].append(f"Error in draft_node: {str(e)}")
        state["status"] = "failed"

    return state