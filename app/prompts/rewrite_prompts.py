REWRITE_PROMPT = """
Rewrite this LinkedIn post applying the critique below.

POST GOAL: {post_goal}

ORIGINAL POST:
{post}

CRITIQUE:
{critique}

TARGETED IMPROVEMENTS:
{targeted_advice}

Fix the PRIORITY FIX first. Everything else is secondary.

HUMAN VOICE (apply whenever the critique says the post reads AI-made):
- Break the even rhythm. Put a 3-4 word line next to a long one.
- Replace one tidy bullet or summary line with a raw artifact: an exact error
  string, a log line, a single line of code, or a non-round number.
- Add one admission or aside in first person ("I still don't know why").
- Use contractions and plain words. Drop any sentence that sounds like it
  was assembled rather than said.
- Remove the closing moral. Stop where the thought stops.
- Do not make it longer by adding filler — cut instead.

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
- Emojis: at most one, only as a marker on a pointer line. Never in the first
  or last line. Remove purely decorative ones (🚀 🔥 💡 🙌 🎯) entirely

FINAL CHECK:
Does line 1 make someone ask "wait, what?" before they see the rest?
If not — rewrite the opening first before anything else.

Return only the rewritten post.
"""