TOPIC_GENERATION_PROMPT = """
You generate LinkedIn post ideas for a working AI engineer in 2026.

TODAY'S DIRECTION — generate an idea specifically within this area:
{topic_bucket}

RECENT TOPICS ALREADY USED — do not repeat or closely resemble any of these:
{recent_topics}

WHAT MAKES A STRONG TOPIC:
A strong topic is a specific contradiction, failure, or counterintuitive
observation — not a theme or a question.

WEAK: "The importance of context engineering"
WEAK: "Why agents fail in production"
STRONG: "Adding more context to the window made our outputs worse, not better"
STRONG: "Our agent passed every eval then broke in the first hour of production"
STRONG: "The human reviewers in our loop were accidentally training the model to please them"

The topic must also naturally support ONE of these post goals:
- IMPRESSIONS: a contradiction or counterintuitive insight worth stopping for
- COMMENTS: an open question or opinion others will react to strongly
- SAVES: a specific failure with a fix that others can apply

Include the post goal in your response like this:
TOPIC: <the topic sentence>
GOAL: <IMPRESSIONS or COMMENTS or SAVES>

Return only TOPIC and GOAL lines. Nothing else.
"""