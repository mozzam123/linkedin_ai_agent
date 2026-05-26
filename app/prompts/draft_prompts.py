DRAFT_GENERATION_PROMPT = """
Read the full style guide below before writing a single word.
Your job is to produce a post that sounds exactly like the examples in it —
same rhythm, same line breaks, same quiet confidence.

===========================================================
STYLE GUIDE:
{style_examples}
===========================================================

TOPIC:
{topic}

RESEARCH — pick one specific detail that makes the post concrete.
Ignore the rest. You only need one real thing, not a summary of everything.
{research}

===========================================================

BEFORE YOU WRITE THE FIRST LINE — stop and answer this internally:

  "What is the entry point for someone reading this cold?"

The reader has no context. They don't know what you're about to talk about.
The first line must give them a reason to care or a moment to step into.

Use one of the two entry types from the style guide:
- A grounded moment: something happened, place the reader inside it
- A shared tension: something they already believe, then complicate it

Do NOT open with the insight. The insight is earned, not announced.

---

THEN WRITE THE POST following these rules:
- Every sentence on its own line
- Blank line after every sentence, no exceptions
- Maximum 12 lines of actual text
- One idea only — do not introduce a second point
- Do not start with "I've been", "Recently", "I noticed", "Let's talk about"
- Do not end by asking the reader a question
- Do not summarize or moralize at the end
- The last line should feel like a quiet stop, not a conclusion
- No bullet points, no headers, no lists

The test before returning:
Read your first line cold, as if you know nothing about the topic.
Does it make you ask a silent "wait, what?" or "yes, and then?"
If not — rewrite the opening until it does.

Return only the post. No labels, no titles, no preamble.
"""