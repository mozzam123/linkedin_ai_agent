from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.llm_service import get_llm 


def research_topic(topic: str) -> str:
    llm = get_llm(temperature=0.4)

    prompt = f"""You are preparing research notes for a LinkedIn post by a technical AI engineer.

Topic: {topic}

Generate 5-7 specific, concrete research points that will help write a sharp post about this topic.

Each point must be:
- Specific to this exact topic — not generic AI observations
- Something a hands-on AI engineer would actually know or have encountered
- Grounded in real technical tradeoffs, patterns, tools, or failure modes
- Written as a short observation, not a headline

Avoid:
- Generic statements like "AI is changing everything"
- Motivational or marketing language
- Points that could apply to any AI topic

Return only the bullet points, nothing else.
"""

    response = llm.invoke(prompt)
    research_notes = f"Research for: {topic}\n\n{response.content.strip()}"
    return research_notes