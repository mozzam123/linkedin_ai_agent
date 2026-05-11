from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.draft_prompts import DRAFT_GENERATION_PROMPT


def draft_node(state):

    llm = get_llm()

    prompt = DRAFT_GENERATION_PROMPT.format(

        topic=state["topic"],

        research=state["research_notes"]

    )

    response = llm.invoke(prompt)

    state["generated_post"] = response.content

    return state