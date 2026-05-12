from app.workflows.state.linkedin_state import LinkedInPostState


async def research_tools_node(state: LinkedInPostState):

    topic = state["topic"]

    tools_research = f"""
    Tools Research for: {topic}

    Key Insights:
    - LangGraph adoption is increasing
    - FastAPI remains popular for AI backends
    - Observability tools are becoming essential
    """

    state["tools_research"] = tools_research

    return state