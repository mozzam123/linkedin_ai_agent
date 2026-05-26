import time
import random
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm
from app.prompts.topic_prompts import TOPIC_GENERATION_PROMPT
from app.db.session import SessionLocal
from app.db.models.post_model import LinkedInPost


def get_recent_topics(limit: int = 10) -> str:
    """
    Reads the last N topics from the DB so the prompt can explicitly
    avoid repeating them
    """
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
    "human-in-the-loop design — where to put checkpoints",
    "eval culture — teams that skip it and what breaks later",
    "agent memory — session vs persistent vs shared",
    "tool use failure patterns — what agents are genuinely bad at",
    "the pilot-to-production gap in agentic AI",
    "how coding agents are changing daily engineering work",
    "when adding more agents makes reliability worse",
    "deterministic logic vs LLM reasoning in production systems",
    "prompt engineering vs context engineering — why context is harder",
    "agent cost optimization — frontier vs smaller models",
    "what agent observability actually looks like in practice",
]


def topic_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        # Pick a random bucket to force a different starting direction each run
        selected_bucket = random.choice(TOPIC_BUCKETS)

        # Pull recent topics from DB so model knows what to avoid
        recent_topics = get_recent_topics(limit=10)

        # Build the prompt with anti-repetition context injected
        prompt = TOPIC_GENERATION_PROMPT.format(
            topic_bucket=selected_bucket,
            recent_topics=recent_topics,
        )

        # High temperature for topic generation — we want creative variety
        llm = get_llm(temperature=0.95)
        response = llm.invoke(prompt)

        state["topic"] = response.content.strip()
        state["status"] = "processing"

    except Exception as e:
        state["errors"].append(f"Error in topic_node: {str(e)}")
        state["status"] = "failed"

    return state