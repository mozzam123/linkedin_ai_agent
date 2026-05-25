from app.workflows.state.linkedin_state import LinkedInPostState
from app.tools.research_tool import research_topic


def research_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        topic = state["topic"]

        if not topic:
            raise ValueError("No topic found in state — topic_node may have failed.")

        research = research_topic(topic)
        state["research_notes"] = research
        state["status"] = "processing"

    except Exception as e:
        state["errors"].append(f"Error in research_node: {str(e)}")
        state["status"] = "failed"

    return state