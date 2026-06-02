DRAFT_GENERATION_PROMPT = """
Read the full style guide below before writing a single word.
Your job is to produce a post that sounds exactly like the examples — same
rhythm, same specificity, same quiet confidence. Not a content creator. An engineer.

===========================================================
STYLE GUIDE:
{style_examples}
===========================================================

TOPIC:
{topic}

RESEARCH — pick ONE specific detail that makes the post concrete and credible.
A number, a named tool, a timeline, a specific failure mode.
Ignore everything else. One anchor beats a full summary every time.
{research}

===========================================================

STEP 1 — BEFORE WRITING, DECIDE THREE THINGS INTERNALLY:

1. ENTRY POINT
   What is the first line a cold reader sees?
   It must create a silent "wait, what?" or "yes — and then what?"
   Choose: contradiction / specific moment / reframe
   Do NOT open with a setup sentence. Start in the tension.

2. THE ONE ANCHOR
   What is the single specific detail from research that proves this is lived experience?
   A number. A named pattern. A specific failure. A timeline.
   If you cannot name one, you are writing theory — start over.

3. THE ENDING
   Does this post want to drive comments, saves, or shares?
   Comments → end with an unresolved observation or genuine question
   Saves   → end with a one-line practical takeaway or named framework
   Shares  → end with a named pattern that gives readers vocabulary

STEP 2 — WRITE THE POST

FORMATTING RULES — these are laws:
- Every sentence on its own line
- Blank line after every sentence, no exceptions
- Maximum 14 lines of actual text
- No headers, no bold, no hashtags, no emojis
- Short fragments are good — even one-word lines work

POINTER RULES — exceptions only:
- Bullets ( • ): only for 3-5 parallel things, max 8 words each, no full stops
- Arrows ( → ): only for cause-effect chains, max 3 in a row, max 6 words each
- Never mix bullets and arrows in the same post
- When in doubt — no pointers, just plain lines

CONTENT RULES:
- One idea only — never introduce a second point
- Do NOT start with "I've been", "Recently", "I noticed", "Let's talk about"
- Do NOT end with "What do you think?" or "Follow me for more"
- Do NOT summarize or wrap up neatly at the end
- No buzzwords: leverage, paradigm, unlock, game-changer, revolutionize,
  seamless, robust, cutting-edge, innovative, ecosystem, transform, empower

STEP 3 — SELF-CHECK BEFORE RETURNING:

Read your first line cold, as if you know nothing about the topic.
Does it create a half-second pause? If not — rewrite the opening.

Is there one specific anchor (number / named pattern / real failure)?
If not — add one. Remove a vague line to make space.

Does the ending leave something open or give something actionable?
If it wraps up too neatly — cut the last line.

Would a real engineer read this and think "someone who actually builds things wrote this"?
If it sounds generated — rewrite until it doesn't.

Return only the post. No labels, no titles, no preamble.
"""