REWRITE_PROMPT = """
Rewrite this LinkedIn post applying the critique below.

POST GOAL: {post_goal}

ORIGINAL POST:
{post}

CRITIQUE:
{critique}

Fix the PRIORITY FIX first. Everything else is secondary.

GOAL-SPECIFIC REWRITE RULES:

If IMPRESSIONS:
- The hook must create a contradiction or half-second confusion before resolving
- Include at least one named pattern (Goodhart's Law, reward hacking, etc.)
- End on a sharp reframe — closed but memorable, not a question

If COMMENTS:
- Open with a grounded moment — something happened, place the reader inside it
- The ending must be a genuine question from real curiosity
- Not "what do you think?" — ask something specific you'd actually want answered

If SAVES:
- Include one specific detail: a number, a timeline, a system name
- Structure: problem → what you found → what you changed → actionable last line
- Someone should be able to screenshot the fix and apply it tomorrow

FORMAT RULES (always apply):
- Every sentence on its own line, blank line between each
- 150-300 words total
- No buzzwords, no filler, no summarizing at the end
- Pointers only if genuinely needed:
  • Bullets: 3-5 parallel items, max 8 words each
  → Arrows: cause-effect only, max 3 in a row
- Never mix bullets and arrows

FINAL CHECK:
Does line 1 make someone ask "wait, what?" before they see the rest?
If not — rewrite the opening first before anything else.

Return only the rewritten post.
"""