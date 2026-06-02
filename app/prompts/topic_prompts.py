TOPIC_GENERATION_PROMPT = """
You generate LinkedIn post ideas for a working AI engineer in 2026.

TODAY'S DIRECTION — generate an idea specifically within this area:
{topic_bucket}

RECENT TOPICS ALREADY USED — do not repeat or closely resemble any of these:
{recent_topics}

The idea must follow ONE of these three proven formats that drive reach:

FORMAT 1 — CONTRADICTION
Something that shouldn't be true but is. Creates instant curiosity.
Example: "Our model scored higher on every eval. Production results got worse."

FORMAT 2 — SPECIFIC MOMENT
A real thing that happened. Places the reader inside an experience.
Example: "On day 3 of debugging we realised the bug wasn't in the code."

FORMAT 3 — REFRAME
What everyone assumes, then the flip.
Example: "Adding more agents to fix reliability usually makes it worse."

Pick the format that fits the topic area naturally.

The idea must be:
- A specific observation, not a broad theme
- Grounded in a real tradeoff, failure, or counterintuitive finding
- Something a working engineer would actually encounter
- Completely different from the recent topics listed above

Do not write: "The importance of X" or "Why X matters"
Do write the actual observation: "X breaks because of Y, not Z"

Return only the topic idea as one sentence. Nothing else.
"""