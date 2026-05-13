from app.workflows.state.linkedin_state import LinkedInPostState
import time
from app.services.llm_service import get_llm


def rewrite_node(state: LinkedInPostState):
    start = time.time()

    llm = get_llm()

    post = state["generated_post"]

    critique = state["critique"]

    prompt = f"""
    Improve this LinkedIn post.

    Original Post:
    {post}

    Critique:
    {critique}

    Improve the post while keeping it:
    - concise
    - authentic
    - engaging
    """

    response = llm.invoke(prompt)

    state["generated_post"] = response.content

    duration = time.time() - start

    # state["trace"].log_step(
    #     "draft_node",
    #     {"topic": state["topic"]},
    #     {"generated_post": response.content},
    #     duration
    # )

    return state