from langgraph.graph import StateGraph, END

from app.workflows.state.linkedin_state import LinkedInPostState

from app.workflows.nodes.topic_node import topic_node
from app.workflows.nodes.draft_node import draft_node
from app.workflows.nodes.critique_node import critique_node
from app.workflows.nodes.rewrite_node import rewrite_node
from app.workflows.nodes.save_node import save_node
from app.workflows.nodes.research_ai_node import research_ai_node
from app.workflows.nodes.research_startup_node import research_startup_node
from app.workflows.nodes.research_tools_node import research_tools_node


graph = StateGraph(LinkedInPostState)


# -----------------------------
# ADD NODES
# -----------------------------

graph.add_node("topic_node", topic_node)

graph.add_node("research_ai_node", research_ai_node)

graph.add_node("research_startup_node", research_startup_node)

graph.add_node("research_tools_node", research_tools_node)

graph.add_node("draft_node", draft_node)

graph.add_node("critique_node", critique_node)

graph.add_node("rewrite_node", rewrite_node)

graph.add_node("save_node", save_node)


# -----------------------------
# ENTRY POINT
# -----------------------------

graph.set_entry_point("topic_node")


# -----------------------------
# NORMAL EDGES
# -----------------------------

graph.add_edge("topic_node", "research_ai_node")

graph.add_edge("topic_node", "research_startup_node")

graph.add_edge("topic_node", "research_tools_node")

graph.add_edge("research_ai_node", "draft_node")

graph.add_edge("research_startup_node", "draft_node")

graph.add_edge("research_tools_node", "draft_node")

graph.add_edge("draft_node", "critique_node")

graph.add_edge("save_node", END)

# -----------------------------
# CONDITIONAL ROUTING
# -----------------------------

def route_after_critique(state: LinkedInPostState):

    score = state.get("score", 0)

    if score >= 8:
        state["status"] = "approved"
        return "save_node"

    if state["iteration_count"] >= 3:
        state["status"] = "max_iterations_reached"
        return "save_node"

    state["status"] = "rewriting"

    return "rewrite_node"


graph.add_conditional_edges(
    "critique_node",
    route_after_critique,
)


# -----------------------------
# REWRITE LOOP
# -----------------------------

graph.add_edge("rewrite_node", "critique_node")


# -----------------------------
# COMPILE WORKFLOW
# -----------------------------

workflow = graph.compile()