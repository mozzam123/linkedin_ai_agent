from langgraph.graph import StateGraph, END

from app.workflows.state.linkedin_state import LinkedInPostState

from app.workflows.nodes.topic_node import topic_node
from app.workflows.nodes.draft_node import draft_node
from app.workflows.nodes.critique_node import critique_node
from app.workflows.nodes.rewrite_node import rewrite_node
from app.workflows.nodes.save_node import save_node
from app.workflows.nodes.research_node import research_node
from app.workflows.nodes.validation_node import validation_node


graph = StateGraph(LinkedInPostState)


# -----------------------------
# ADD NODES
# -----------------------------

graph.add_node("topic_node", topic_node)
graph.add_node("research_node", research_node)
graph.add_node("draft_node", draft_node)
graph.add_node("critique_node", critique_node)
graph.add_node("rewrite_node", rewrite_node)
graph.add_node("validation_node", validation_node)
graph.add_node("save_node", save_node)


# -----------------------------
# ENTRY POINT
# -----------------------------

graph.set_entry_point("topic_node")


# -----------------------------
# NORMAL EDGES
# -----------------------------

graph.add_edge("topic_node", "research_node")

graph.add_edge("research_node", "draft_node")

graph.add_edge("draft_node", "critique_node")

graph.add_edge("save_node", END)

# -----------------------------
# CONDITIONAL ROUTING
# -----------------------------

def route_after_critique(state: LinkedInPostState):

    score = state.get("score", 0)

    if score >= 8:
        return "validation_node"

    if state["iteration_count"] >= 3:
        state["status"] = "max_iterations_reached"
        return "validation_node"

    state["status"] = "rewriting"
    return "rewrite_node"


graph.add_conditional_edges(
    "critique_node",
    route_after_critique,
    {
        "validation_node": "validation_node",
        "rewrite_node": "rewrite_node",
        "save_node": "save_node"  # Fallback target if global failure happens
    }
)


# -----------------------------
# CONDITIONAL ROUTING (VALIDATION)
# -----------------------------
# NEW: Determines where to go after content rules are validated
def route_after_validation(state: LinkedInPostState):
    # If the validation node itself or something upstream caught a code exception
    if state.get("status") == "failed":
        return "save_node"

    # If it fails content rules (spam hashtags, too long) and we haven't looped too much,
    # send it back to the rewrite loop to automatically optimize it.
    if not state.get("is_valid", True) and state.get("iteration_count", 0) < 3:
        # Append an explicit instruction for the rewrite node to consume via state if desired
        state["critique"] = (state.get("critique", "") + 
                             "\nAdditionally, fix these validation issues: " + 
                             ", ".join(state.get("validation_errors", [])))
        return "rewrite_node"

    # Content is safe or loop limits were hit; proceed to save
    return "save_node"


graph.add_conditional_edges(
    "validation_node",
    route_after_validation,
    {
        "rewrite_node": "rewrite_node",
        "save_node": "save_node"
    }
)

# -----------------------------
# REWRITE LOOP
# -----------------------------

graph.add_edge("rewrite_node", "critique_node")


# -----------------------------
# COMPILE WORKFLOW
# -----------------------------

workflow = graph.compile()