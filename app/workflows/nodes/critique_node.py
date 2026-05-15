import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.schemas.evaluation_schema import PostEvaluation

def critique_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
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

        response = structured_llm.invoke(prompt)
        state["score"] = response.score
        state["critique"] = response.feedback
        
    except Exception as e:
        state["errors"].append(f"Error in critique_node: {str(e)}")
        state["status"] = "failed"

    return state