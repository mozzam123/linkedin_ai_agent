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

HUMAN FEEL (1-10)
Judge the VOICE only — ignore whether the idea is good.

Signals that it was written by a real engineer (each one earns credit):
- Uneven rhythm: a 3-word line next to a long run-on one. Perfectly even
  sentence lengths are the single biggest AI tell.
- One raw artifact: an exact log line, error string, real code line, a
  non-round number (27.4%, 11:42pm), a tool name nobody would invent.
- An admission or aside: "I still don't know why" / "we were wrong about
  this for a week" / a parenthetical thought.
- Contractions and plain words ("didn't", "basically", "honestly").
- Asymmetry: the post does NOT go neatly setup → 3 problems → 3 fixes →
  lesson. Tidy symmetry, matched bullet lists, and a closing moral are
  machine shapes.
- Ending that just stops, instead of landing a manufactured insight.

Scoring bands:
- 9-10: reads like a Slack message from someone who shipped it. Messy,
  specific, slightly unresolved.
- 7-8: clearly human, but one or two lines are still polished.
- 5-6: competent and clearly LLM-shaped — even cadence, tidy lists, no
  admission, correct but bloodless.
- 3-4: templated. Symmetric structure, bullets where prose belongs, every
  sentence the same length, ends on a lesson.
- 1-2: corporate/motivational, "In today's world", buzzwords, "What do
  you think?" ending.

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