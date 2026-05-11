from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.topic_prompts import TOPIC_GENERATION_PROMPT


def topic_node(state):

    llm = get_llm()

    response = llm.invoke(TOPIC_GENERATION_PROMPT)

    state["topic"] = response.content.strip()

    return state