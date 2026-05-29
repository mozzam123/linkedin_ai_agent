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

FORMATTING:
- Every sentence on its own line
- Blank line after every sentence, no exceptions
- Maximum 12 lines of actual text (bullet/arrow lines count individually)
- No headers, no bold, no hashtags, no emojis
 
POINTERS — only when the content genuinely calls for it:
- Bullets ( • ): listing 3-5 parallel things, max 8 words each, no full stops
- Arrows ( → ): cause-effect or reveal, max 3 in a row, max 6 words each
- Never mix bullets and arrows in the same post
- When in doubt — skip pointers entirely and write plain lines
 
CONTENT:
- One idea only
- Do not start with "I've been", "Recently", "I noticed", "Let's talk about"
- Do not end by asking the reader a question
- Do not summarize or moralize at the end
- No buzzwords: leverage, paradigm, unlock, game-changer, revolutionize,
  seamless, robust, cutting-edge, innovative, ecosystem, transform
 
THE TEST before returning:
- Read the first line cold — does it make you ask "wait, what?" or "yes, and?"
- If pointers were used — was there genuinely a list or a chain? Or just habit?
- Does it sound like a person or a generator?
 
Return only the post. No labels, no titles, no preamble.
"""