from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm


def topic_node(state: LinkedInPostState):

    llm = get_llm()

    prompt = """
    Generate ONE trending LinkedIn post topic related to:
    - AI engineering
    - LLMs
    - FastAPI
    - AI agents
    - developer productivity
    - startups

    The topic should:
    - be relevant in 2026
    - sound insightful
    - have strong engagement potential

    Return only the topic.
    """

    response = llm.invoke(prompt)

    state["topic"] = response.content.strip()

    return state