"""Sends a Slack alert for the latest eval run.

Requires SLACK_WEBHOOK_URL in .env (Slack -> your workspace -> Apps ->
Incoming Webhooks -> Add to Slack -> pick a channel -> copy the URL).

Run: python send_alert.py [--current runs/x.json] [--baseline runs/y.json] [--report-link URL]
"""

import argparse
import os

from dotenv import load_dotenv

from src.alerting import send_slack_alert
from src.comparator import compare_runs
from src.drift import detect_drift
from src.evaluator import list_run_files, load_eval_run


def main() -> None:
    load_dotenv()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise SystemExit(
            "SLACK_WEBHOOK_URL is not set in .env. Create an Incoming Webhook "
            "in your Slack workspace (Apps -> Incoming Webhooks) and add it "
            "to .env before running this."
        )

    parser = argparse.ArgumentParser()
    parser.add_argument("--current")
    parser.add_argument("--baseline")
    parser.add_argument("--report-link", default=None)
    args = parser.parse_args()

    files = [str(f) for f in list_run_files()]
    if not files:
        raise SystemExit("No runs found in /runs. Run python run_eval.py first.")

    current_path = args.current or files[-1]
    if args.baseline:
        baseline_path = args.baseline
    elif current_path in files and files.index(current_path) > 0:
        baseline_path = files[files.index(current_path) - 1]
    else:
        baseline_path = None

    current = load_eval_run(current_path)
    baseline = load_eval_run(baseline_path) if baseline_path else None
    comparison = compare_runs(baseline, current) if baseline else None
    history = [load_eval_run(f) for f in files]
    drift = detect_drift(history) if len(history) >= 2 else None

    send_slack_alert(webhook_url, current, comparison, args.report_link, drift)
    print("Slack alert sent.")


if __name__ == "__main__":
    main()
