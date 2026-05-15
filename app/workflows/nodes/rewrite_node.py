import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm

def rewrite_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
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
        state["iteration_count"] += 1
        
    except Exception as e:
        state["errors"].append(f"Error in rewrite_node: {str(e)}")
        state["status"] = "failed"

    return state