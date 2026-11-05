from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.validator_service import validate_linkedin_content

def validation_node(state: LinkedInPostState) -> LinkedInPostState:
    # Initialize fields safely
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []
    state["validation_errors"] = []
    state["is_valid"] = True

    try:
        # Validate the best version we have, which is what will be saved
        post_content = state.get("best_post") or state.get("generated_post", "")
        topic = state.get("topic", "")

        if not post_content:
            state["validation_errors"].append("No content found to validate.")
            state["is_valid"] = False
            return state

        # Run checks — validate_linkedin_content returns (is_valid, errors, advisories)
        is_valid, errors, advisories = validate_linkedin_content(post_content, topic=topic)

        state["validation_errors"] = list(errors) + list(advisories)
        state["is_valid"] = is_valid
        
        # If the content failed critical validation thresholds, adjust status
        if not is_valid:
            # We can label it flag-reviewed so conditional routers know to send it back to rewrite
            state["status"] = "failed_validation"
        else:
            state["status"] = "validated"

    except Exception as e:
        state["errors"].append(f"Error in validation_node: {str(e)}")
        state["status"] = "failed"
        state["is_valid"] = False

    return state