CRITIQUE_PROMPT = """
Evaluate this LinkedIn post for a technical AI audience.

Post:
{post}

For each area below, give a score (1-10) AND one specific improvement:
- Hook: Is the first line scroll-stopping?
- Clarity: Is the core insight clear within 3 lines?  
- Authenticity: Does it sound like a real engineer, not a content template?
- Pacing: Are paragraphs short? Is there enough whitespace?
- Ending: Does it end with something memorable or a genuine question?

Then write: "PRIORITY FIX: [the single most important thing to change]"
"""