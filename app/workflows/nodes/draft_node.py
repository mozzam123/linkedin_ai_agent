import time
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT


def draft_node(state):

    start = time.time()

    llm = get_llm()

    prompt = DRAFT_GENERATION_PROMPT.format(

        topic=state["topic"],

        research=state["research_notes"]

    )

    response = llm.invoke(prompt)

    state["generated_post"] = response.content

    duration = time.time() - start

    state["trace"].log_step(
        "draft_node",
        {"topic": state["topic"]},
        {"generated_post": response.content},
        duration
    )

    return state