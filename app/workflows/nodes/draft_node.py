from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm


def draft_node(state: LinkedInPostState):

    llm = get_llm()

    topic = state["topic"]

    prompt = f"""
    You are an expert LinkedIn content writer.

    Write a high-quality LinkedIn post about:

    Topic:
    {topic}

    Style:
    - professional
    - insightful
    - concise
    - engaging
    - easy to read

    Keep it authentic and practical.
    """

    response = llm.invoke(prompt)

    state["generated_post"] = response.content

    return state