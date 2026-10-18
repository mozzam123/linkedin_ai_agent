from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm


def research_distillation_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        llm = get_llm(temperature=0.0)  # deterministic for extraction
        research = state.get("research_notes") or ""

        if not research:
            state["extracted_facts"] = []
            return state

        prompt = f"""
        Extract concrete, specific details from the following research text that could be used to make a LinkedIn post more credible and rich.
        Look for:
        - Specific numbers (percentages, timelines, quantities)
        - Named systems, tools, or methodologies
        - Specific events or outcomes
        - Avoid vague statements.
        Return each detail as a separate line, maximum 5 details.
        If no concrete details are found, return an empty list.

        RESEARCH TEXT:
        {research}

        CONCRETE DETAILS (one per line):
        """

        response = llm.invoke(prompt)
        lines = [line.strip() for line in response.content.strip().split('\n') if line.strip()]
        # Filter out empty lines and limit to 5
        facts = lines[:5]
        state["extracted_facts"] = facts

    except Exception as e:
        state["errors"].append(f"Error in research_distillation_node: {str(e)}")
        state["extracted_facts"] = []

    return state