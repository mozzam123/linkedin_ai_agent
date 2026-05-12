from app.workflows.state.linkedin_state import LinkedInPostState


async def research_ai_node(state: LinkedInPostState):

    topic = state["topic"]

    ai_research = f"""
    AI Research for: {topic}

    Key Insights:
    - AI workflows are replacing prompt-only systems
    - Structured orchestration is becoming critical
    - Evaluation loops improve reliability
    - Multi-agent systems are increasingly common
    """

    state["ai_research"] = ai_research

    return state