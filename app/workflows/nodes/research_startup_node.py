from app.workflows.state.linkedin_state import LinkedInPostState


async def research_startup_node(state: LinkedInPostState):

    topic = state["topic"]

    startup_research = f"""
    Startup Research for: {topic}

    Key Insights:
    - Startups are rapidly adopting AI workflows
    - Lean AI teams prefer orchestration systems
    - AI automation reduces operational overhead
    """

    state["startup_research"] = startup_research

    return state