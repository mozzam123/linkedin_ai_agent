import random
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.topic_prompts import TOPIC_GENERATION_PROMPT
from app.db.session import SessionLocal
from app.db.models.post_model import LinkedInPost


def get_recent_topics(limit: int = 10) -> str:
    try:
        db = SessionLocal()
        recent = (
            db.query(LinkedInPost.topic)
            .filter(LinkedInPost.topic.isnot(None))
            .order_by(LinkedInPost.id.desc())
            .limit(limit)
            .all()
        )
        db.close()
        if not recent:
            return "None yet."
        return "\n".join(f"- {row.topic}" for row in recent)
    except Exception:
        return "None yet."


# All available topic buckets — one is picked randomly each run
# so even if the model drifts, the starting point is always different
TOPIC_BUCKETS = [
    "context engineering and what goes into a context window",
    "why agents fail in production when they worked fine in testing",
    "orchestration tradeoffs — one smart agent vs many specialized agents",
    "cost reality of running LLMs at scale",
    "human-in-the-loop design — where to put checkpoints and what goes wrong",
    "eval culture — teams that skip it and what breaks later",
    "agent memory — session vs persistent vs shared",
    "tool use failure patterns — what agents are genuinely bad at",
    "the pilot-to-production gap in agentic AI",
    "how coding agents are changing daily engineering work",
    "when adding more agents makes reliability worse",
    "deterministic logic vs LLM reasoning — when each breaks",
    "prompt engineering vs context engineering — why context is harder",
    "agent cost optimization — frontier vs smaller models",
    "reward hacking and misaligned objectives in AI systems",
    "what agent observability actually looks like in practice",
    "why most AI evals don't catch production failures",
    "the hidden cost of human review in training pipelines",
]


def _parse_topic_response(raw: str) -> tuple[str, str]:
    """
    Parse TOPIC and GOAL from model response.
    Returns (topic, goal) — goal defaults to IMPRESSIONS if not found.
    """
    topic = ""
    goal  = "IMPRESSIONS"
 
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("TOPIC:"):
            topic = line[6:].strip()
        elif line.upper().startswith("GOAL:"):
            raw_goal = line[5:].strip().upper()
            if raw_goal in ("IMPRESSIONS", "COMMENTS", "SAVES"):
                goal = raw_goal
 
    # Fallback if model returned plain text without labels
    if not topic:
        topic = raw.strip().splitlines()[0].strip()
 
    return topic, goal


def topic_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []
 
    try:
        selected_bucket = random.choice(TOPIC_BUCKETS)
        recent_topics   = get_recent_topics(limit=10)
 
        prompt = TOPIC_GENERATION_PROMPT.format(
            topic_bucket=selected_bucket,
            recent_topics=recent_topics,
        )
 
        llm      = get_llm(temperature=0.95)
        response = llm.invoke(prompt)
 
        topic, goal = _parse_topic_response(response.content)
 
        state["topic"]     = topic
        state["post_goal"] = goal
        state["status"]    = "processing"
 
    except Exception as e:
        state["errors"].append(f"Error in topic_node: {str(e)}")
        state["status"] = "failed"
 
    return state