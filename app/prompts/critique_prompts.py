CRITIQUE_PROMPT = """
You are evaluating a LinkedIn post written by a working AI engineer.
Be harsh. A post that sounds even slightly AI-generated or generic should score below 6.

POST GOAL: {post_goal}
(IMPRESSIONS = reach, COMMENTS = discussion, SAVES = reference value)

POST TO EVALUATE:
{post}

Score each dimension 1-10:

HOOK (1-10)
Does line 1 create a genuine "wait, what?" moment before "See more" is clicked?
A setup sentence scores 3 or below. A contradiction or tension scores 7+.

ENTRY POINT (1-10)
Does the opening place the reader inside a moment, contradiction, or shared tension?
Or does it just describe what happened? Description = low score.

SPECIFICITY (1-10)
Is there at least one concrete detail — a number, a timeline, a named system?
Zero specifics = 4 or below. One good anchor = 7+.

HUMAN FEEL (1-10) — score it mechanically, do not go by vibe:
Start at 5, then add and subtract:

ADD 1 for each signal that is actually present (max +4):
  a) RHYTHM: line and paragraph lengths visibly vary — a short line sits
     next to a longer paragraph. Every sentence isolated on its own line,
     or every sentence the same length, does NOT earn this.
  b) ARTIFACT: an exact error string, log line, code fragment, or a
     non-round number (41.2%, 11:42pm). Round numbers like 40% do not count.
  c) ADMISSION: first-person uncertainty or being wrong — "I still don't
     know why", "we were wrong about this for a week", a real aside.
  d) PLAIN SPEECH: contractions and ordinary words, no corporate or
     motivational phrasing anywhere.

SUBTRACT 1 for each machine tell present (max -3):
  - a tidy symmetric list or problem→fix→lesson shape where prose belongs
  - a closing moral, lesson, or manufactured insight
  - perfectly uniform cadence, or every single sentence on its own line

Clamp the result to 1-10 and report that number.

Do not punish brevity or fragments — fragments are evidence of a human.
Punish polish, symmetry, and tidy resolution.

GOAL ALIGNMENT (1-10)
IMPRESSIONS goal: does it end on a named pattern or sharp reframe?
COMMENTS goal: does it end on a genuine open question?
SAVES goal: does it include a fix and end on an actionable line?

DWELL TIME (1-10)
Would a reader pause 10+ seconds on this? Is there a moment mid-post
where they slow down to process something surprising?

If HUMAN FEEL is below 6, the priority_fix MUST quote the exact line(s)
that read machine-made and name the fix (e.g. "the three ✅ bullets in a row
are symmetric — replace with one raw log line").

Then write exactly:
PRIORITY FIX: <single most important change — be specific, not generic>
OVERALL SCORE: <average of all six scores as one number>

Respond in this exact JSON format, nothing else:
{{
  "hook": <score>,
  "entry_point": <score>,
  "specificity": <score>,
  "human_feel": <score>,
  "goal_alignment": <score>,
  "dwell_time": <score>,
  "priority_fix": "<specific fix>",
  "overall_score": <score>
}}
"""