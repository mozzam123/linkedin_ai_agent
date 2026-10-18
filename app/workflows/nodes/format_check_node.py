import re
from app.workflows.state.linkedin_state import LinkedInPostState
from app.services.llm_service import get_llm


def format_check_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        post = state.get("generated_post") or ""
        if not post:
            return state

        # Check compliance
        violations = check_format_compliance(post)

        if not violations:
            # Format is compliant, nothing to do
            return state

        # If not compliant, ask LLM to fix the format
        llm = get_llm(temperature=0.2)
        prompt = f"""
        The following LinkedIn post violates some format rules. Please rewrite it to strictly comply with the format rules below.
        Keep the content and meaning as close as possible to the original, but adjust formatting to meet the rules.

        FORMAT RULES:
        1. Every sentence must be on its own line.
        2. There must be a blank line after every sentence.
        3. Total word count must be between 150 and 300 words.
        4. No headers, no bold, no hashtags in the body.
        5. Pointers (bullets or arrows) should only be used when genuinely needed:
           - Bullets: only for 3-5 parallel items, max 8 words each.
           - Arrows: only for cause-effect chains, max 3 in a row.
           - Never mix bullets and arrows in the same post.
           - Most posts should have zero pointers.

        ORIGINAL POST:
        {post}

        REWRITTEN POST (format-compliant):
        """

        response = llm.invoke(prompt)
        fixed_post = response.content.strip()

        # Update the state
        state["generated_post"] = fixed_post
        state["final_post"] = fixed_post  # Keep in sync

    except Exception as e:
        state["errors"].append(f"Error in format_check_node: {str(e)}")

    return state


def check_format_compliance(post: str) -> list:
    """
    Returns a list of violation messages. Empty list if compliant.
    """
    violations = []

    # Rule 1 & 2: Every sentence on its own line, blank line after every sentence.
    # We'll split by lines and check pattern.
    lines = post.split('\n')
    # We expect pattern: sentence line, blank line, sentence line, blank line, ... possibly ending with a sentence line and no blank line after? The rule says blank line after every sentence, always.
    # So we expect even-numbered lines (0-indexed) to be sentences, odd-numbered lines to be blank.
    # However, the post might not end with a blank line. The rule says blank line after every sentence, so the last line should be a sentence and then there should be a blank line? But if it's the end, maybe it's okay not to have a blank line after the last sentence? The examples in the style guide show blank line after every sentence, including the last? Let's look at the examples: they have blank line after each sentence, and the last sentence is followed by a blank line? Actually, in the examples, there is a blank line after each sentence, and then the next sentence starts after a blank line. At the end of the example, there is a blank line before the next section? Hard to tell.
    # We'll be lenient: we require that between sentences there is exactly one blank line. We'll allow the post to start with a sentence line and end with a sentence line (no trailing blank line).
    # We'll check that there are no two consecutive non-empty lines (since that would mean a sentence without a blank line after it) and no two consecutive blank lines (except maybe at the end?).
    # We'll implement a simple check: split by blank lines (two or more newlines) to get potential sentences.
    # Then check that each sentence line does not contain a newline (i.e., is a single line) and that the original post has blank lines between them.

    # Instead, let's use a regex to check for the pattern: we want to ensure that there are no two non-empty lines consecutive.
    # Also, we want to ensure that there are no lines with more than one sentence (i.e., a line containing two sentences separated by a space and a capital letter? Hard).
    # We'll do a simple check: if there are any two consecutive non-empty lines, that's a violation.
    # Also, we want to ensure that each line that is not empty ends with a punctuation (., !, ?) or is a short fragment? The style guide allows short fragments.
    # We'll skip the punctuation check for now.

    # Check for consecutive non-empty lines
    prev_empty = True  # start with empty so first line can be non-empty
    for line in lines:
        if line.strip() == '':
            if not prev_empty:
                # We just had a non-empty line, now empty -> good, we expect a blank line after a sentence.
                pass
            prev_empty = True
        else:
            if not prev_empty:
                # We have two non-empty lines in a row
                violations.append("Two consecutive non-empty lines found (missing blank line between sentences).")
            prev_empty = False

    # Rule 3: Word count between 150 and 300
    word_count = len(post.split())
    if word_count < 150:
        violations.append(f"Word count too low: {word_count}. Minimum 150.")
    if word_count > 300:
        violations.append(f"Word count too high: {word_count}. Maximum 300.")

    # Rule 4: No headers, no bold, no hashtags in the body.
    # We'll check for markdown-style headers (lines starting with #) and bold (** or __) and hashtags (#word)
    # But note: the style guide says no headers, no bold, no hashtags in the body.
    # We'll check for lines that start with # (header) and for ** or __ inside lines, and for # followed by alphanumeric (hashtag).
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            violations.append(f"Line {i+1}: Header-like line starting with '#'.")
        if re.search(r'\*\*|__', line):
            violations.append(f"Line {i+1}: Bold markup detected.")
        # Hashtag: # followed by letters/numbers, not part of a URL? We'll just check for #word
        if re.search(r'#\w+', line):
            violations.append(f"Line {i+1}: Hashtag detected.")

    # Rule 5: Pointers (bullets and arrows)
    # We'll check for lines that start with bullet-like patterns (e.g., '- ', '* ') or arrow patterns ('->')
    # We'll also check that we don't mix bullets and arrows in the same post.
    bullet_lines = []
    arrow_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('• '):
            bullet_lines.append(i+1)
        if '→' in stripped or '->' in stripped:
            arrow_lines.append(i+1)
    if bullet_lines and arrow_lines:
        violations.append(f"Mixing bullets (lines {bullet_lines}) and arrows (lines {arrow_lines}) in the same post.")
    # Check for too many bullets in a row? We'll skip for simplicity.
    # Check for bullet lines that are too long? We'll skip.

    return violations