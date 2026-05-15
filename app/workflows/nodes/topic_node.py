import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.topic_prompts import TOPIC_GENERATION_PROMPT

def topic_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        start = time.time()
        llm = get_llm()
        response = llm.invoke(TOPIC_GENERATION_PROMPT)
        
        state["topic"] = response.content.strip()
        state["status"] = "processing"  # Track healthy progress

    except Exception as e:
        state["errors"].append(f"Error in topic_node: {str(e)}")
        state["status"] = "failed"
        
    return state