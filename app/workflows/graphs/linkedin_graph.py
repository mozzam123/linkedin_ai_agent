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

# ── Nodes ──────────────────────────────────────────────────────────────────────
graph.add_node("topic_node",      topic_node)
graph.add_node("research_node",   research_node)
graph.add_node("draft_node",      draft_node)
graph.add_node("critique_node",   critique_node)
graph.add_node("rewrite_node",    rewrite_node)
graph.add_node("validation_node", validation_node)
graph.add_node("save_node",       save_node)

# ── Entry ──────────────────────────────────────────────────────────────────────
graph.set_entry_point("topic_node")

# ── Fixed edges ────────────────────────────────────────────────────────────────
graph.add_edge("topic_node",    "research_node")
graph.add_edge("research_node", "draft_node")
graph.add_edge("draft_node",    "critique_node")
graph.add_edge("rewrite_node",  "critique_node")
graph.add_edge("save_node",     END)


# ── Router: after critique ─────────────────────────────────────────────────────
def route_after_critique(state: LinkedInPostState):
    # Always coerce to float — never let None reach the comparison
    score          = float(state.get("score") or 0.0)
    iteration_count = int(state.get("iteration_count") or 0)

    if state.get("status") == "failed":
        return "save_node"

    if score >= 8:
        return "validation_node"

    if iteration_count >= 3:
        state["status"] = "max_iterations_reached"
        return "validation_node"

    state["status"] = "rewriting"
    return "rewrite_node"


graph.add_conditional_edges(
    "critique_node",
    route_after_critique,
    {
        "validation_node": "validation_node",
        "rewrite_node":    "rewrite_node",
        "save_node":       "save_node",
    }
)


# ── Router: after validation ───────────────────────────────────────────────────
def route_after_validation(state: LinkedInPostState):
    if state.get("status") == "failed":
        return "save_node"

    iteration_count = int(state.get("iteration_count") or 0)

    if not state.get("is_valid", True) and iteration_count < 3:
        state["critique"] = (
            (state.get("critique") or "") +
            "\nAdditionally, fix these validation issues: " +
            ", ".join(state.get("validation_errors") or [])
        )
        return "rewrite_node"

    return "save_node"


graph.add_conditional_edges(
    "validation_node",
    route_after_validation,
    {
        "rewrite_node": "rewrite_node",
        "save_node":    "save_node",
    }
)

# ── Compile ────────────────────────────────────────────────────────────────────
workflow = graph.compile()