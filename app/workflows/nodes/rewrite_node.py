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

        prompt = f"""Rewrite this LinkedIn post applying the critique below.

Original Post:
{post}

Critique:
{critique}

Rules:
- Fix the PRIORITY FIX first
- Keep the core insight intact — don't invent new content
- Keep it under 200 words
- Every paragraph max 2 sentences
- Don't add emojis or hashtags unless they were in the original
- The new version must feel sharper, not longer

Return only the rewritten post.
"""

        response = llm.invoke(prompt)
        state["generated_post"] = response.content

        # Always keep final_post in sync with the latest rewrite
        # This fixes the bug where final_post was saving the original draft
        state["final_post"] = response.content

        state["iteration_count"] += 1

    except Exception as e:
        state["errors"].append(f"Error in rewrite_node: {str(e)}")
        state["status"] = "failed"

    return state