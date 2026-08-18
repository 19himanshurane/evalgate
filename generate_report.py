"""Builds the self-contained HTML report for the latest eval run.

Run: python generate_report.py [--current runs/x.json] [--baseline runs/y.json]
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.comparator import compare_runs
from src.drift import detect_drift
from src.evaluator import list_run_files, load_eval_run
from src.report import generate_html_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current")
    parser.add_argument("--baseline")
    args = parser.parse_args()

    files = [str(f) for f in list_run_files()]
    if not files:
        raise SystemExit("No runs found in /runs. Run python run_eval.py first.")

    current_path = args.current or files[-1]

    if args.baseline:
        baseline_path = args.baseline
    elif current_path in files and files.index(current_path) > 0:
        # Default baseline is whichever run immediately precedes the
        # chosen "current" run -- not just "second-newest file overall",
        # which silently compares runs in the wrong direction if
        # --current points at anything other than the latest run.
        baseline_path = files[files.index(current_path) - 1]
    else:
        baseline_path = None

    current = load_eval_run(current_path)
    baseline = load_eval_run(baseline_path) if baseline_path else None
    comparison = compare_runs(baseline, current) if baseline else None
    history = [load_eval_run(f) for f in files]
    drift = detect_drift(history) if len(history) >= 2 else None

    html = generate_html_report(current, baseline, comparison, history, drift)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"reports/report_{current.prompt_version}_{run_id}.html"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
