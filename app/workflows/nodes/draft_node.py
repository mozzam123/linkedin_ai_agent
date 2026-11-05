import time
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT
from app.utils.style_loader import load_style_examples


def draft_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        # Formatting rules are enforced in code by format_check_node, so the
        # FORMATTING section is left out of the prompt to save tokens.
        style_examples = load_style_examples(exclude_headings=("formatting",))
        # reasoning_effort="low" matters: with the provider default, hidden
        # reasoning tokens consume the whole max_tokens budget and the model
        # returns an empty response.
        llm            = get_llm(temperature=0.7, max_tokens=1500, reasoning_effort="low")

        # post_goal tells the draft exactly what to optimise for
        post_goal = state.get("post_goal") or "IMPRESSIONS"

        # Format extracted facts as a bulleted list
        extracted_facts = state.get("extracted_facts") or []
        facts_text = "\n".join([f"- {fact}" for fact in extracted_facts]) if extracted_facts else "No specific facts extracted."

        # Truncate research notes if too long to avoid context limit issues
        # and to keep each call inside the per-minute token budget
        research_notes = state.get("research_notes") or ""
        if len(research_notes) > 1200:
            research_notes = research_notes[:1200] + "... [truncated]"

        # Use the normal prompt for actual topic-based generation
        prompt = DRAFT_GENERATION_PROMPT.format(
            topic=state["topic"],
            research=research_notes,
            style_examples=style_examples,
            post_goal=post_goal,
            extracted_facts=facts_text,
        )

        response               = llm.invoke(prompt)
        # Check if we got valid content
        if response.content and isinstance(response.content, str) and response.content.strip():
            state["generated_post"] = response.content
            state["final_post"]     = response.content  # Keep in sync from first draft
        else:
            # Fallback to simpler prompt if the complex one didn't work
            fallback_prompt = f"Write a short LinkedIn post about {state['topic']}. Make it engaging and professional. Aim for 150-300 words."
            fallback_response = llm.invoke(fallback_prompt)
            if fallback_response.content and isinstance(fallback_response.content, str) and fallback_response.content.strip():
                state["generated_post"] = fallback_response.content
                state["final_post"]     = fallback_response.content
            else:
                # Last resort: set a default message indicating the issue
                state["generated_post"] = f"[Draft generation failed for topic: {state['topic']}. Please try again.]"
                state["final_post"]     = state["generated_post"]

        # Track the best version seen; a later rewrite is only kept if it scores higher
        if state.get("generated_post"):
            state["best_post"]  = state["generated_post"]
            state["best_score"] = None

    except Exception as e:
        state["errors"].append(f"Error in draft_node: {str(e)}")
        state["status"] = "failed"
        # Even on error, set something so the workflow can continue
        state["generated_post"] = f"[Error generating draft: {str(e)}]"
        state["final_post"]     = state["generated_post"]

    return state