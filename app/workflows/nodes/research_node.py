from app.workflows.state.linkedin_state import LinkedInPostState
from app.tools.research_tool import research_topic

def research_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        topic = state["topic"]
        research = research_topic(topic)
        state["research_notes"] = research
        
    except Exception as e:
        state["errors"].append(f"Error in research_node: {str(e)}")
        state["status"] = "failed"

    return state