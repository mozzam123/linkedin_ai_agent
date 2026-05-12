from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.topic_prompts import TOPIC_GENERATION_PROMPT
import time

async def topic_node(state):

    start = time.time()

    llm = get_llm()

    response = await llm.invoke(TOPIC_GENERATION_PROMPT)

    state["topic"] = response.content.strip()

    duration = time.time() - start

    state["trace"].log_step(
        "draft_node",
        {"topic": state["topic"]},
        {"generated_post": response.content},
        duration
    )

    return state