TOPIC_GENERATION_PROMPT = """
You generate LinkedIn post ideas for a working AI engineer in 2026.

TODAY'S DIRECTION — generate an idea specifically within this area:
{topic_bucket}

RECENT TOPICS ALREADY USED — do not repeat or closely resemble any of these:
{recent_topics}

The idea must be:
- A specific observation, not a broad theme
- Something that would surprise or resonate with a working engineer
- Grounded in a real tradeoff, failure, or counterintuitive insight
- Completely different in angle from the recent topics listed above
- Expressible in one sharp sentence

Do not write: "The importance of X" or "Why X matters"
Do write: "Adding more agents usually makes the reliability problem worse, not better"

Return only the topic sentence. Nothing else.
"""