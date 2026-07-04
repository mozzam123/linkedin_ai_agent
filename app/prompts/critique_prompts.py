CRITIQUE_PROMPT = f"""
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

HUMAN FEEL (1-10)
Does it sound like a real engineer or like a content generator?
Any AI polish, any corporate phrase, any motivational echo = below 6.

GOAL ALIGNMENT (1-10)
IMPRESSIONS goal: does it end on a named pattern or sharp reframe?
COMMENTS goal: does it end on a genuine open question?
SAVES goal: does it include a fix and end on an actionable line?

DWELL TIME (1-10)
Would a reader pause 10+ seconds on this? Is there a moment mid-post
where they slow down to process something surprising?

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