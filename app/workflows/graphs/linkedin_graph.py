from langgraph.graph import StateGraph, END

from app.workflows.state.linkedin_state import LinkedInPostState

from app.workflows.nodes.topic_node import topic_node
from app.workflows.nodes.draft_node import draft_node
from app.workflows.nodes.critique_node import critique_node
from app.workflows.nodes.rewrite_node import rewrite_node


graph = StateGraph(LinkedInPostState)

graph.add_node("topic_node", topic_node)
graph.add_node("draft_node", draft_node)
graph.add_node("critique_node", critique_node)
graph.add_node("rewrite_node", rewrite_node)

graph.set_entry_point("topic_node")

graph.add_edge("topic_node", "draft_node")
graph.add_edge("draft_node", "critique_node")


def route_after_critique(state: LinkedInPostState):

    score = state["score"]

    if score >= 8:
        return END
    
    if state["iteration_count"] >= 3:
        return END

    return "rewrite_node"


graph.add_conditional_edges(
    "critique_node",
    route_after_critique,
)

graph.add_edge("rewrite_node", "critique_node")

workflow = graph.compile()