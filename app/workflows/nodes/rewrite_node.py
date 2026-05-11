from app.workflows.state.linkedin_state import LinkedInPostState

from app.services.llm_service import get_llm


def rewrite_node(state: LinkedInPostState):

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

    return state