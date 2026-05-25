REWRITE_PROMPT = """
Rewrite this LinkedIn post applying the critique below.

Original Post:
{post}

Critique:
{critique}

Rules:
- Fix the PRIORITY FIX first
- Keep the core insight intact — don't invent new content
- Keep it under 200 words
- Every paragraph max 2 sentences
- Don't add emojis or hashtags
- The new version must feel sharper, not longer

Return only the rewritten post.
"""