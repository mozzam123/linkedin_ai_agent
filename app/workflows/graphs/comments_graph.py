from langgraph.graph import StateGraph, END

from app.workflows.nodes.comments.discovery_node import discovery_node
from app.workflows.nodes.comments.generate_node import generate_node
from app.workflows.nodes.comments.relevance_node import relevance_node
from app.workflows.state.comment_state import CommentWorkflowState

graph = StateGraph(CommentWorkflowState)

graph.add_node("discovery_node", discovery_node)
graph.add_node("relevance_node", relevance_node)
graph.add_node("generate_node", generate_node)

graph.set_entry_point("discovery_node")


def route_after_discovery(state: CommentWorkflowState):
    if state.get("status") == "failed":
        return "end"
    return "relevance"


def route_after_relevance(state: CommentWorkflowState):
    if state.get("status") == "failed":
        return "end"
    if not state.get("selected_posts"):
        return "end"  # nothing worth commenting on this run
    return "generate"


graph.add_conditional_edges(
    "discovery_node",
    route_after_discovery,
    {"relevance": "relevance_node", "end": END},
)

graph.add_conditional_edges(
    "relevance_node",
    route_after_relevance,
    {"generate": "generate_node", "end": END},
)

graph.add_edge("generate_node", END)

comment_workflow = graph.compile()
