DRAFT_GENERATION_PROMPT = """
Read the full style guide below before writing a single word.
Your job is to produce a post that matches the voice, rhythm, and structure
of the examples exactly — while optimising for the stated post goal.

===========================================================
STYLE GUIDE:
{style_examples}
===========================================================

TOPIC:
{topic}

POST GOAL:
{post_goal}

RESEARCH — pick ONE specific detail that makes the post concrete and credible.
One real number, one real timeline, one specific system detail.
Ignore everything else in the research. You only need one anchor.
{research}

===========================================================

BEFORE WRITING — answer these internally:

1. ENTRY POINT
   What is the entry point for someone reading this cold?
   Pick one:
   - Contradiction: two things that shouldn't both be true
   - Grounded moment: something happened, place the reader inside it
   - Shared tension: something they believe, then you complicate it
   Do NOT open with a setup sentence. Do NOT announce the insight cold.

2. POST GOAL STRUCTURE
   If IMPRESSIONS: contradiction hook → realisation moment → named pattern → sharp reframe
   If COMMENTS: grounded moment → discovery → genuine open question at the end
   If SAVES: problem → specific detail (number/timeline) → what changed → actionable last line

3. SPECIFICITY CHECK
   Have you included at least one concrete detail — a number, a timeline,
   a specific system name, a real failure mode?
   If not, pull one from the research or invent a plausible specific.
   Vague posts don't get saves or shares.

4. NAMING CHECK
   If this post describes a known failure mode or pattern, name it.
   Goodhart's Law, reward hacking, context pollution, prompt brittleness —
   named patterns get shared. Unnamed observations stay personal.

---

THEN WRITE THE POST:

Format rules (non-negotiable):
- Every sentence on its own line
- Blank line after every sentence, always
- 150-300 words total
- No headers, no bold, no hashtags in the body
- Pointers only when content genuinely calls for it:
  • Bullets: 3-5 parallel items, max 8 words each
  → Arrows: cause-effect chain only, max 3 in a row
  Never mix both in one post. Default is no pointers.

Ending rules by goal:
- IMPRESSIONS: end on a named pattern or sharp reframe. Closed but memorable.
- COMMENTS: end on a genuine question from real curiosity. Not "what do you think?"
- SAVES: end on one actionable line the reader can apply tomorrow.

Content rules:
- One idea only
- No buzzwords (leverage, unlock, transform, seamless, robust, game-changer)
- No filler phrases ("In today's world", "It's no secret that")
- No summarizing at the end
- No moral or lesson statement

FINAL TEST before returning:
Read line one cold, as someone who knows nothing about this topic.
Does it make you ask "wait, what?" or "yes — and then what?"
If not, rewrite the opening until it does.

Return only the post. No labels, no titles, no preamble.
"""