"""Slack incoming-webhook alerting. Sends a structured summary of an eval
run (and its comparison against the baseline, if any) to a Slack channel."""

import httpx

from src.models import ComparisonResult, DriftResult, EvalRun

STATUS_EMOJI = {
    "critical": "🚨",
    "warning": "⚠️",
    "ok": "✅",
    "improved": "🎉",
    None: "ℹ️",
}
STATUS_LABEL = {
    "critical": "CRITICAL REGRESSION",
    "warning": "WARNING",
    "ok": "PASS",
    "improved": "IMPROVED",
    None: "FIRST RUN",
}


def build_slack_payload(
    current: EvalRun,
    comparison: ComparisonResult | None,
    report_link: str | None = None,
    drift: DriftResult | None = None,
) -> dict:
    severity = comparison.severity if comparison else None
    emoji = STATUS_EMOJI[severity]
    label = STATUS_LABEL[severity]

    if comparison:
        delta_sign = "+" if comparison.pass_rate_delta >= 0 else ""
        headline = (
            f"Pass rate {current.pass_rate:.1%} ({delta_sign}{comparison.pass_rate_delta:.1%}) "
            f"— {len(comparison.regressions)} regression(s), {len(comparison.improvements)} improvement(s)"
        )
    else:
        headline = f"Pass rate {current.pass_rate:.1%} — first recorded run, no baseline to compare"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} evalgate: {label}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": headline},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Prompt `{current.prompt_version}` · Model `{current.model}` "
                        f"· Dataset `{current.dataset_version}` · {current.timestamp}"
                    ),
                }
            ],
        },
    ]

    if comparison and comparison.regressions:
        case_list = ", ".join(f.case_id for f in comparison.regressions[:10])
        more = f" (+{len(comparison.regressions) - 10} more)" if len(comparison.regressions) > 10 else ""
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Regressed cases:* {case_list}{more}"},
            }
        )

    if drift and drift.is_drifting:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":chart_with_downwards_trend: *Slow drift detected* — "
                        f"{drift.window}-run average is {drift.current_moving_avg:.1%}, "
                        f"down {drift.drift:.1%} from its best of {drift.best_moving_avg:.1%}. "
                        f"No single run triggered this, only the trend."
                    ),
                },
            }
        )

    if report_link:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<{report_link}|View full report>"},
            }
        )

    return {"blocks": blocks}


def send_slack_alert(
    webhook_url: str,
    current: EvalRun,
    comparison: ComparisonResult | None,
    report_link: str | None = None,
    drift: DriftResult | None = None,
) -> None:
    payload = build_slack_payload(current, comparison, report_link, drift)
    response = httpx.post(webhook_url, json=payload, timeout=10.0)
    response.raise_for_status()
