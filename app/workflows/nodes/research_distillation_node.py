"""
Extract concrete facts from the research notes.

This used to make a second LLM call over text the research node had *just*
generated — roughly 2.7k prompt tokens per run for reformatting bullet points.
The research output is already a bulleted list, so the extraction is done
deterministically now: same result, zero tokens, zero latency.
"""

import re

from app.workflows.state.linkedin_state import LinkedInPostState

MAX_FACTS = 5
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_CONCRETE = re.compile(r"\d|%|→|->|:")  # numbers, percentages, cause chains, named things


def research_distillation_node(state: LinkedInPostState):
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []

    research = state.get("research_notes") or ""
    if not research.strip():
        state["extracted_facts"] = []
        return state

    lines = []
    for raw in research.splitlines():
        line = _BULLET_PREFIX.sub("", raw).strip()
        if not line or line.lower().startswith(("research for:", "research:")):
            continue
        lines.append(line)

    # Prefer lines carrying something concrete (a number, a name, a mechanism)
    concrete = [l for l in lines if _CONCRETE.search(l)]
    ordered = concrete + [l for l in lines if l not in concrete]

    state["extracted_facts"] = ordered[:MAX_FACTS]
    return state
