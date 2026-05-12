from app.workflows.state.linkedin_state import LinkedInPostState

from app.services.llm_service import get_llm

from app.schemas.evaluation_schema import PostEvaluation
import time


async def critique_node(state: LinkedInPostState):

    start = time.time()

    llm = get_llm()

    structured_llm = llm.with_structured_output(PostEvaluation)

    post = state["generated_post"]

    prompt = f"""
    Evaluate this LinkedIn post.

    Post:
    {post}

    Evaluate:
    - clarity
    - engagement
    - authenticity
    - readability
    - hook quality

    Return:
    - score out of 10
    - concise feedback
    """

    response = await structured_llm.invoke(prompt)

    state["score"] = response.score
    state["critique"] = response.feedback

    duration = time.time() - start

    state["trace"].log_step(
        "draft_node",
        {"topic": state["topic"]},
        {"generated_post": response.content},
        duration
    )

    return state