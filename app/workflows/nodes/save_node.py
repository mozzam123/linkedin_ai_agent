from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.workflow_service import save_workflow_run
from app.services.post_service import save_post

def save_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        state["status"] = "under_review"
        
        # Save actions executed sequentially
        save_post(state)
        save_workflow_run(state)
        
    except Exception as e:
        state["errors"].append(f"Error in save_node: {str(e)}")
        state["status"] = "failed"
        # We still attempt to save the failed state metrics if database layer is alive
        try:
            save_workflow_run(state)
        except Exception:
            pass

    return state



    