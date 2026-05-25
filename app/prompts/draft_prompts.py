DRAFT_GENERATION_PROMPT = """
You are writing a LinkedIn post in the voice of a working AI engineer.

Study the style guide below carefully before writing anything.
Your post must feel like it came from the same person who wrote those examples —
same rhythm, same bluntness, same breathing room between lines.

---

STYLE GUIDE:
{style_examples}

---

TOPIC:
{topic}

RESEARCH NOTES — use these for specific details, not as a script:
{research}

---

NOW WRITE THE POST.

Hard rules:
- Do NOT start with "I've been", "Recently", "I noticed", "In today's world"
- Do NOT use: leverage, paradigm, unlock, game-changer, revolutionize, seamless,
  robust, cutting-edge, innovative, ecosystem, empower, transform, groundbreaking
- Do NOT write more than 2 sentences without a blank line
- Do NOT summarize — make one sharp point and stop
- Do NOT add a moral at the end
- Do NOT explain what you're about to say — just say it
- Do NOT sound like you're performing insight — sound like you're sharing it

The post should feel like someone typed it at their desk after a long day,
not generated it.

Return only the post. No titles, no labels, no preamble.
"""