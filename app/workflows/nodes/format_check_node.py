"""
Deterministic format enforcement for generated posts.

This used to call the LLM to reformat the post. That had two problems:
  1. it added one of the slowest calls of the run (measured 8-21s), on every
     pass through the rewrite loop, and
  2. when the model returned an empty response the post was overwritten with
     an empty string, silently destroying the draft.

Formatting is a mechanical rule, so it is applied with string operations now:
no network call, instant, and it can never return empty.
"""

import re

from app.workflows.state.linkedin_state import LinkedInPostState

# Splitting on sentence enders, but never after a known abbreviation
_ABBREVIATIONS = (
    "e.g", "i.e", "etc", "vs", "Mr", "Mrs", "Ms", "Dr", "Prof", "Inc",
    "Ltd", "No", "approx", "a.m", "p.m", "U.S", "St",
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_BULLET = re.compile(r"^(?:[-*•]|\d+[.)]|→|->)\s+")
_ARROW = re.compile(r"(?:→|->)")

# Pictographic emoji only — bullets/arrows are handled separately
_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]\uFE0F?")
MAX_EMOJIS = 2


def _limit_emojis(text: str, limit: int = MAX_EMOJIS) -> str:
    """Emojis are allowed only as occasional markers, so extras are dropped."""
    matches = list(_EMOJI.finditer(text))
    if len(matches) <= limit:
        return text
    for match in reversed(matches[limit:]):
        text = text[: match.start()] + text[match.end():]
    # A removed marker can leave a leading space, so re-tidy each line
    lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def _split_sentences(text: str) -> list[str]:
    """Split a paragraph into sentences, protecting common abbreviations."""
    parts = _SENTENCE_END.split(text.strip())
    sentences: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # If the previous sentence ends with an abbreviation, re-join them
        if sentences and sentences[-1].rstrip(".").lower().endswith(_ABBREVIATIONS):
            sentences[-1] = f"{sentences[-1]} {part}"
        else:
            sentences.append(part)
    return sentences


def _depoetify(text: str) -> str:
    """
    The model mirrors the style examples' one-sentence-per-line layout even when
    told not to. When nearly every block is a single sentence, regroup them into
    2-3 sentence paragraphs. Pointer/code blocks are left untouched.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) < 8:
        return text

    def is_pointer(block: str) -> bool:
        return bool(
            _BULLET.match(block)
            or _ARROW.search(block)
            or block.lstrip().startswith(("`", "```"))
        )

    single_sentence = sum(
        1
        for b in blocks
        if not is_pointer(b)
        and "\n" not in b
        and (b.count(".") + b.count("!") + b.count("?")) <= 1
    )
    if single_sentence / len(blocks) < 0.8:
        return text

    out: list[str] = []
    buffer: list[str] = []

    def flush():
        while buffer:
            out.append(" ".join(buffer[:3]))
            del buffer[:3]

    for block in blocks:
        if is_pointer(block):
            flush()
            out.append(block)
        else:
            buffer.append(block)
    flush()

    return "\n\n".join(out)


def normalize_post(post: str) -> str:
    """
    Apply the house format rules without an LLM:
      - no markdown headers / bold
      - paragraph structure is preserved (1-3 sentences per paragraph is fine)
      - whitespace tidied: no trailing spaces, single blank line between blocks
    Sentence-per-line is no longer forced — that cadence was the loudest
    "AI-written" tell in the critique.
    """
    if not post:
        return post

    text = post.replace("\r\n", "\n")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)          # **bold**
    text = re.sub(r"__(.+?)__", r"\1", text)              # __bold__
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)  # # headers

    out: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", raw_line).strip()
        if not line:
            # Collapse runs of blank lines into a single paragraph break
            if out and out[-1] != "":
                out.append("")
            continue
        if _BULLET.match(line) or _ARROW.search(line):
            # Keep pointer lines together as one list block
            if out and out[-1] == "" and len(out) >= 2 and _BULLET.match(out[-2] or ""):
                out.pop()
            out.append(line)
            continue
        out.append(line)
        # A paragraph break after a pointer block keeps lists readable
        if _BULLET.match(line):
            out.append("")

    while out and out[-1] == "":
        out.pop()

    normalized = "\n".join(out).strip()
    normalized = _depoetify(normalized)
    normalized = _limit_emojis(normalized)
    return normalized or post


def check_format_compliance(post: str) -> list[str]:
    """Returns a list of violation messages. Empty list if compliant."""
    violations: list[str] = []
    lines = post.split("\n")

    # Rule 1: no single line should be a wall of text
    for i, line in enumerate(lines):
        if len(line.strip()) > 400:
            violations.append(
                f"Line {i + 1} is {len(line.strip())} characters — break it up."
            )
            break

    # Rule 2: word count between 150 and 300
    word_count = len(post.split())
    if word_count < 150:
        violations.append(f"Word count too low: {word_count}. Minimum 150.")
    if word_count > 300:
        violations.append(f"Word count too high: {word_count}. Maximum 300.")

    # Rule 3: no headers, bold or hashtags in the body
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            violations.append(f"Line {i + 1}: Header-like line starting with '#'.")
        if re.search(r"\*\*|__", line):
            violations.append(f"Line {i + 1}: Bold markup detected.")
        if re.search(r"#\w+", line):
            violations.append(f"Line {i + 1}: Hashtag detected.")

    # Rule 4b: emojis only as rare markers
    emoji_count = len(_EMOJI.findall(post))
    if emoji_count > MAX_EMOJIS:
        violations.append(
            f"Too many emojis: {emoji_count}. Keep it to {MAX_EMOJIS} at most."
        )

    # Rule 5: bullets and arrows must not be mixed
    bullet_lines, arrow_lines = [], []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _BULLET.match(stripped):
            bullet_lines.append(i + 1)
        elif _ARROW.search(stripped):
            arrow_lines.append(i + 1)
    if bullet_lines and arrow_lines:
        violations.append(
            f"Mixing bullets (lines {bullet_lines}) and arrows (lines {arrow_lines}) in the same post."
        )

    return violations


def format_check_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    try:
        post = state.get("generated_post") or ""
        if not post.strip():
            return state

        if not check_format_compliance(post):
            return state

        fixed = normalize_post(post)
        # Never let a failed normalization blank out a real draft
        if fixed and fixed.strip():
            state["generated_post"] = fixed
            state["final_post"] = fixed

    except Exception as e:
        state["errors"].append(f"Error in format_check_node: {str(e)}")

    return state
