from app.workflows.state.linkedin_state import LinkedInPostState

from app.tools.research_tool import research_topic


def research_node(state: LinkedInPostState):

    topic = state["topic"]

    research = research_topic(topic)

    state["research_notes"] = research

    return state