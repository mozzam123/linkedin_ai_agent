import time
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT


async def draft_node(state):

    start = time.time()

    llm = get_llm()

    research_context = f"""

    AI Research:
    {state.get("ai_research")}


    Startup Research:
    {state.get("startup_research")}


    Tools Research:
    {state.get("tools_research")}

    """

    prompt = DRAFT_GENERATION_PROMPT.format(
        topic=state["topic"],
        research=research_context
    )

    response = await llm.invoke(prompt)

    state["generated_post"] = response.content

    duration = time.time() - start

    state["trace"].log_step(
        "draft_node",
        {"topic": state["topic"]},
        {"generated_post": response.content},
        duration
    )

    return state