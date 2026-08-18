"""Diffs two eval runs and reports what changed.

Defaults to the two most recent runs in /runs (current = latest, baseline =
one before it). Exits with a non-zero status on a "critical" regression --
this is what Phase 5's CI step will use to block a merge.

Run: python compare_runs.py [--baseline runs/x.json] [--current runs/y.json]
"""

import argparse
import os
import sys

from src.comparator import CRITICAL_THRESHOLD, WARNING_THRESHOLD, build_pr_comment_markdown, compare_runs
from src.evaluator import list_run_files, load_eval_run


def _two_most_recent_runs() -> tuple[str, str]:
    files = list_run_files()
    if len(files) < 2:
        raise SystemExit(
            f"Need at least 2 runs in /runs to compare, found {len(files)}. "
            "Run python run_eval.py again after changing the prompt."
        )
    return str(files[-2]), str(files[-1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline")
    parser.add_argument("--current")
    parser.add_argument("--markdown-out", help="Write a PR-comment-ready markdown summary to this path")
    args = parser.parse_args()

    if args.baseline and args.current:
        baseline_path, current_path = args.baseline, args.current
    else:
        baseline_path, current_path = _two_most_recent_runs()

    baseline = load_eval_run(baseline_path)
    current = load_eval_run(current_path)

    # Configurable per the brief -- via env vars so the Docker container
    # (Phase 5) can tune sensitivity without a code change or rebuild.
    warning_threshold = float(os.environ.get("EVAL_WARNING_THRESHOLD", WARNING_THRESHOLD))
    critical_threshold = float(os.environ.get("EVAL_CRITICAL_THRESHOLD", CRITICAL_THRESHOLD))

    print(f"Baseline: {baseline_path}  (prompt {baseline.prompt_version}, pass rate {baseline.pass_rate:.1%})")
    print(f"Current:  {current_path}  (prompt {current.prompt_version}, pass rate {current.pass_rate:.1%})")

    result = compare_runs(baseline, current, warning_threshold, critical_threshold)

    sign = "+" if result.pass_rate_delta >= 0 else ""
    print(f"\nPass rate delta: {sign}{result.pass_rate_delta:.1%}  -> severity: {result.severity.upper()}")

    print("\nPer-category accuracy delta:")
    for cat, delta in sorted(result.per_category_accuracy_delta.items()):
        sign = "+" if delta >= 0 else ""
        print(f"  {cat:10s} {sign}{delta:.1%}")

    if result.regressions:
        print(f"\n{len(result.regressions)} REGRESSION(S) (passed before, failing now):")
        for f in result.regressions:
            print(
                f"  {f.case_id}: expected={f.expected_category} "
                f"{f.baseline_predicted} -> {f.current_predicted} "
                f"(summary {f.baseline_summary_score} -> {f.current_summary_score})"
            )
    else:
        print("\nNo regressions.")

    if result.improvements:
        print(f"\n{len(result.improvements)} improvement(s) (failing before, passing now):")
        for f in result.improvements:
            print(
                f"  {f.case_id}: expected={f.expected_category} "
                f"{f.baseline_predicted} -> {f.current_predicted}"
            )

    if args.markdown_out:
        with open(args.markdown_out, "w", encoding="utf-8") as f:
            f.write(build_pr_comment_markdown(current, baseline, result))
        print(f"\nWrote PR comment markdown to {args.markdown_out}")

    if result.severity == "critical":
        print("\nCRITICAL regression -- this would block a merge in CI.")
        sys.exit(1)


if __name__ == "__main__":
    main()
