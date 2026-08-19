# Loom walkthrough script (~3 minutes)

Goal: prove the loop works, not explain every file. Someone watching
should come away thinking "oh, this actually runs," not "that's a lot
of code." Talk while you do these, don't just narrate after the fact.

## Before you hit record

- Have these tabs/windows ready: this repo in an editor, a terminal,
  the GitHub repo in a browser, the Slack channel, and one of the
  generated HTML reports already open.
- Know your two headline numbers cold: **84% → 100%** pass rate across
  v1→v3, and the real CI bugs you caught (see below) — those are the
  two things worth remembering if someone only half-watches.

## 0:00–0:20 — The problem, fast

"Teams ship prompt changes constantly, but almost nobody tests them
before they ship — they just eyeball a few outputs and hope. This is
a CI/CD pipeline that catches quality regressions in an LLM feature
automatically, the same way a test suite catches a broken build."

Show: the repo's file tree for two seconds, then cut to the terminal.

## 0:20–1:00 — Change a prompt, run the eval

Open `prompts/email_classifier_v3.yaml` next to `v4`, point at the one
real change: the explicit tie-break rule for multi-issue emails. Say
*why* it exists — "v3 already handled this correctly by accident;
this makes the reasoning an explicit rule instead of implicit luck."

Run:
```bash
python run_eval.py --prompt prompts/email_classifier_v4.yaml
```
Let it print the summary (pass rate, per-category accuracy, failing
cases). Don't wait out the full 5-8 minutes on camera — cut here, or
speed up the footage, and say "this takes a few minutes against a
free-tier rate limit" so it doesn't look like you're hiding a failure.

## 1:00–1:40 — Diff it and show the report

```bash
python compare_runs.py
python generate_report.py
```

Open the generated HTML report. Point at, specifically:
- the scorecard (pass rate delta, category accuracy delta)
- the regressions table (or "no regressions" banner)
- the trend chart across all runs so far

Say the real number: "going from v1 to v3, this actually caught and
fixed a real weak spot — the `account` category was at 43% because it
overlapped conceptually with `billing`. That's not a hypothetical,
that's a number this tool produced."

## 1:40–2:15 — Slack alert

Switch to Slack, show a real alert message from the `evalgate` app —
pass/fail status, headline numbers, regressed case IDs. "This is what
a teammate sees without ever opening the repo."

## 2:15–2:50 — CI actually gating a PR

Switch to the GitHub PR (or a screenshot of one, if the branch is
already deleted) showing the pipeline's own comment and a green check.
Say the one detail that makes this credible, not just theoretical:
"I actually opened a real PR to test this, and it caught two genuine
bugs that only showed up in CI — the reports folder didn't exist on a
fresh checkout, and an unset GitHub Actions variable turned into an
empty string instead of nothing, which crashed threshold parsing. I
wouldn't have found either one without actually running this for
real, not just writing the code and assuming it worked."

## 2:50–3:00 — Close

"That's the whole loop: change a prompt, get scored automatically,
see exactly what changed, and it either ships or it doesn't — without
anyone needing to remember to check by hand."

## What NOT to do

- Don't read code line-by-line on camera.
- Don't apologize for the free-tier latency — explain it once, briefly,
  and move on.
- Don't claim 100% pass rate means the classifier is perfect — if
  asked, the honest line is "it means it stopped failing on the cases
  we thought to test for, and the dataset should keep growing from
  real failures."
