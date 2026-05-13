from app.services.workflow_service import save_workflow_run
from app.workflows.state.linkedin_state import LinkedInPostState

from app.services.post_service import save_post


def save_node(state: LinkedInPostState):

    state["status"] = "under_review"

    save_post(state)
    save_workflow_run(state)

    return state