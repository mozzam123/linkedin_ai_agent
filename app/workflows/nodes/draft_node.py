import time
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT
from app.utils.style_loader import load_style_examples


def draft_node(state):

    style_examples = load_style_examples()

    llm = get_llm()

    prompt = DRAFT_GENERATION_PROMPT.format(
        topic=state["topic"],
        research=state["research_notes"],
        style_examples=style_examples
    )

    response = llm.invoke(prompt)

    state["generated_post"] = response.content

    # duration = time.time() - start

    # state["trace"].log_step(
    #     "draft_node",
    #     {"topic": state["topic"]},
    #     {"generated_post": response.content},
    #     duration
    # )

    return state