# Why I built CI/CD for a prompt, not just an LLM feature

Most people building with LLMs ship prompt changes the same way people
shipped code before automated testing existed: write it, read the
output a few times, and if it looks fine, ship it. There's no test
suite, no diff, no gate — just vibes and a hope that nothing important
broke.

That bothered me enough to build [evalgate](https://github.com/19himanshurane/evalgate):
a small CI/CD pipeline that runs a customer support email classifier
against a golden dataset on every prompt change, scores it on more
than "did the category match," diffs it against the last known-good
version, and blocks a merge if it's a real regression. The classifier
itself isn't the point. The harness around it is.

## The approach

Every piece maps to a software-engineering primitive on purpose:

- **Prompts are versioned files**, not strings buried in code, so
  diffing two prompt versions is the same primitive as diffing two
  commits.
- **A golden dataset is the test suite** — 50 hand-verified emails
  with known-correct answers, run through the classifier on every
  change.
- **Scoring is multi-dimensional.** Category accuracy is cheap and
  binary, but a prompt change that keeps accuracy flat while quietly
  making summaries worse, or triples latency, is still a regression.
  So a second, larger model grades summary quality (an "LLM-as-judge"),
  and I track latency and token cost per case too.
- **A GitHub Action runs the whole thing on every PR**, posts the
  results as a comment, and fails the check on a critical regression.

Used for real, this actually worked: the first baseline run scored
84%, and the diff pointed at exactly why — the `account` category was
at 43%, because it overlapped conceptually with `billing` in ways the
prompt didn't disambiguate. Two targeted prompt fixes later, informed
by that specific diagnosis rather than guesswork, it was at 100%. That
loop — run, find a specific failure, fix it, confirm nothing else
broke — is the entire value proposition in miniature.

## The design decision I'm most glad I made: separating drift from diffs

Per-run diffing catches an obvious problem: change the prompt, pass
rate drops 10%, block the merge. But it's structurally blind to a
slower failure mode — a prompt that erodes by 1% every change for ten
changes straight. Each individual step is noise-sized. Nothing ever
crosses an 8%, or even 3%, single-run threshold. The model quietly
gets worse over months and nobody's alert ever fires.

So drift detection is a separate mechanism, not a lower threshold on
the same check: a rolling average of pass rate across the last seven
runs, compared against its own historical best. If today's average is
meaningfully below the best it's ever been, that's a signal — even
though not one individual run tripped anything. It's a completely
different question from "did this change break something" — it's "is
the thing we're not directly changing quietly getting worse anyway,"
and it needed its own answer instead of being bolted onto the existing
check as an edge case.

## The part that made this feel like real engineering, not a demo

I could've stopped once the code looked right locally. Instead I
opened an actual pull request against my own repo to prove the GitHub
Action worked end to end — and it caught two genuine bugs I'd never
have found by reading the code:

1. `reports/` didn't exist on a fresh CI checkout. It only ever held
   gitignored `.html` files locally, so git never tracked the
   directory itself — trivially true on my machine, where I'd created
   it once by hand and forgotten about it.
2. An unset GitHub Actions repository variable expands to an **empty
   string**, not an absent one. `os.environ.get(key, default)` only
   falls back on a missing key, so `float("")` crashed before it ever
   reached the code that mattered.

Neither is exotic. Both are exactly the kind of thing that only
exists at the boundary between "works on my machine" and "works in
the environment that actually matters" — and the entire reason I found
them is that I insisted on watching a real PR run in a real CI
environment instead of trusting that passing tests locally meant it
was done. That's the same instinct the whole project is built to
encode: don't assume, measure, and specifically don't assume you're
finished until you've watched the real thing actually run.
