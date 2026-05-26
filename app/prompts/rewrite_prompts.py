REWRITE_PROMPT = """
Rewrite this LinkedIn post based on the critique below.

ORIGINAL POST:
{post}

CRITIQUE:
{critique}

Fix the PRIORITY FIX first. Everything else is secondary.

Strict rules for the rewrite:
- Every sentence on its own line, blank line after each
- Maximum 12 lines of actual text
- One idea only — if the original wandered, cut ruthlessly
- No summaries, no morals, no "here's what this means"
- No questions directed at the reader
- No corporate language
- The first line must create tension or state something specific — not ease in
- The last line must feel like a quiet stop, not a conclusion

The rewrite should feel like the engineer edited their own draft at 11pm —
tighter, more direct, less performative.

Return only the rewritten post.
"""