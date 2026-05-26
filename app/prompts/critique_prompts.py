CRITIQUE_PROMPT = """
You are evaluating a LinkedIn post written in the voice of a working AI engineer.

POST TO EVALUATE:
{post}

Score it on these five things (1-10 each):

HOOK — Does the first line create tension or curiosity without being clickbait?
HUMAN FEEL — Does it sound like a person or a generator?
LINE BREAKS — Is every sentence on its own line with a blank line after it?
SINGLE IDEA — Does it make exactly one point without drifting?
ENDING — Does it land quietly without summarizing or moralizing?

Then write exactly this:
PRIORITY FIX: [one sentence describing the single most important thing to change]
OVERALL SCORE: [average of the five scores as a single number]

Be harsh. A post that sounds even slightly like AI-generated content should
score below 6 on HUMAN FEEL.
"""