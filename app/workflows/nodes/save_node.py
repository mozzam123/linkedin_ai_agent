from app.workflows.state.linkedin_state import LinkedInPostState

from app.services.post_service import save_post


def save_node(state: LinkedInPostState):

    state["status"] = "under_review"

    save_post(state)



    return state