"""Generates a self-contained HTML report from eval run(s) -- no external
CSS/JS/CDN dependencies, so the file is portable and safe to email, attach
to a Slack message, or commit to /reports for historical reference."""

from src.models import CaseResult, ComparisonResult, DriftResult, EvalRun

GOOD = "#16a34a"
BAD = "#dc2626"
NEUTRAL = "#6b7280"


def _delta_span(delta: float, fmt, higher_is_better: bool = True) -> str:
    if abs(delta) < 1e-9:
        return f'<span style="color:{NEUTRAL}">no change</span>'
    good = (delta > 0) == higher_is_better
    color = GOOD if good else BAD
    arrow = "▲" if delta > 0 else "▼"
    # Reuse the same formatter as the value columns so the delta's
    # magnitude is never silently rounded away (e.g. a 0.18/5 summary
    # score drop showing as "0" because a percent formatter was applied
    # to a non-percent metric).
    return f'<span style="color:{color};font-weight:600">{arrow} {fmt(abs(delta))}</span>'


def _scorecard_row(label: str, current, baseline, fmt, higher_is_better: bool = True) -> str:
    current_str = fmt(current)
    if baseline is None:
        return f"<tr><td>{label}</td><td>{current_str}</td><td colspan='2' style='color:{NEUTRAL}'>no baseline</td></tr>"
    delta = current - baseline
    return (
        f"<tr><td>{label}</td><td>{current_str}</td><td>{fmt(baseline)}</td>"
        f"<td>{_delta_span(delta, fmt, higher_is_better)}</td></tr>"
    )


def _case_row(f) -> str:
    return (
        f"<tr><td>{f.case_id}</td><td>{f.expected_category}</td>"
        f"<td>{f.baseline_predicted}</td><td>{f.current_predicted}</td>"
        f"<td>{f.baseline_summary_score}</td><td>{f.current_summary_score}</td></tr>"
    )


def _failures_table(results: list[CaseResult]) -> str:
    failing = [r for r in results if not r.passed]
    if not failing:
        return f'<p style="color:{GOOD};font-weight:600">No failing cases.</p>'
    rows = "".join(
        f"<tr><td>{r.case_id}</td><td>{r.difficulty}</td><td>{r.expected_category}</td>"
        f"<td>{r.predicted_category}</td><td>{r.summary_score}/5</td>"
        f"<td class='email-cell'>{r.expected_summary}</td>"
        f"<td class='email-cell'>{r.predicted_summary}</td></tr>"
        for r in failing
    )
    return f"""
    <table>
      <thead><tr><th>Case</th><th>Difficulty</th><th>Expected</th><th>Predicted</th>
      <th>Summary score</th><th>Expected summary</th><th>Predicted summary</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _trend_svg(history: list[EvalRun]) -> str:
    if len(history) < 2:
        return "<p>Need at least 2 runs for a trend chart.</p>"

    width, height, pad = 640, 220, 40
    plot_w, plot_h = width - 2 * pad, height - 2 * pad
    n = len(history)
    step = plot_w / (n - 1)

    def y_of(pass_rate: float) -> float:
        return pad + plot_h * (1 - pass_rate)

    points = [(pad + i * step, y_of(r.pass_rate)) for i, r in enumerate(history)]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    gridlines = "".join(
        f'<line x1="{pad}" y1="{pad + plot_h * f:.1f}" x2="{pad + plot_w}" y2="{pad + plot_h * f:.1f}" '
        f'stroke="#e5e7eb" stroke-width="1"/>'
        f'<text x="{pad - 8}" y="{pad + plot_h * f + 4:.1f}" font-size="11" fill="{NEUTRAL}" text-anchor="end">{int((1 - f) * 100)}%</text>'
        for f in (0, 0.25, 0.5, 0.75, 1.0)
    )
    dots_and_labels = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{GOOD if history[i].pass_rate >= 0.9 else BAD if history[i].pass_rate < 0.7 else "#d97706"}"/>'
        f'<text x="{x:.1f}" y="{height - pad + 20}" font-size="11" fill="{NEUTRAL}" text-anchor="middle">{history[i].prompt_version}</text>'
        for i, (x, y) in enumerate(points)
    )

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">
      {gridlines}
      <polyline points="{polyline}" fill="none" stroke="#2563eb" stroke-width="2"/>
      {dots_and_labels}
    </svg>"""


def _drift_banner(drift: DriftResult | None) -> str:
    if drift is None:
        return ""
    if drift.is_drifting:
        return (
            f'<div class="banner" style="border-color:#d97706;color:#d97706">'
            f"SLOW DRIFT DETECTED &mdash; {drift.window}-run moving average is "
            f"{drift.current_moving_avg:.1%}, down {drift.drift:.1%} from its best "
            f"of {drift.best_moving_avg:.1%}. No single run triggered a regression, "
            f"but the trend is declining.</div>"
        )
    return (
        f'<div class="meta">{drift.window}-run moving average: {drift.current_moving_avg:.1%} '
        f"(best: {drift.best_moving_avg:.1%}) &middot; no drift detected</div>"
    )


def generate_html_report(
    current: EvalRun,
    baseline: EvalRun | None,
    comparison: ComparisonResult | None,
    history: list[EvalRun],
    drift: DriftResult | None = None,
) -> str:
    scorecard = "".join(
        [
            _scorecard_row("Pass rate", current.pass_rate, baseline.pass_rate if baseline else None, lambda v: f"{v:.1%}"),
            _scorecard_row("Category accuracy", current.category_accuracy, baseline.category_accuracy if baseline else None, lambda v: f"{v:.1%}"),
            _scorecard_row("Avg summary score", current.avg_summary_score, baseline.avg_summary_score if baseline else None, lambda v: f"{v:.2f}/5"),
            _scorecard_row("Avg latency", current.avg_latency_ms, baseline.avg_latency_ms if baseline else None, lambda v: f"{v:.0f}ms", higher_is_better=False),
            _scorecard_row("Total tokens", current.total_tokens, baseline.total_tokens if baseline else None, lambda v: f"{v:,}", higher_is_better=False),
        ]
    )

    if comparison:
        severity_color = {"critical": BAD, "warning": "#d97706", "ok": NEUTRAL, "improved": GOOD}[comparison.severity]
        status_banner = (
            f'<div class="banner" style="border-color:{severity_color};color:{severity_color}">'
            f"{comparison.severity.upper()} &mdash; pass rate {comparison.pass_rate_delta:+.1%}, "
            f"{len(comparison.regressions)} regression(s), {len(comparison.improvements)} improvement(s)"
            f"</div>"
        )
        regressions_html = (
            f"<table><thead><tr><th>Case</th><th>Expected</th><th>Baseline predicted</th>"
            f"<th>Current predicted</th><th>Baseline score</th><th>Current score</th></tr></thead>"
            f"<tbody>{''.join(_case_row(f) for f in comparison.regressions)}</tbody></table>"
            if comparison.regressions
            else f'<p style="color:{GOOD};font-weight:600">No regressions.</p>'
        )
    else:
        status_banner = '<div class="banner" style="border-color:#6b7280;color:#6b7280">No baseline available for this run (first run).</div>'
        regressions_html = "<p>N/A</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>evalgate report -- {current.prompt_version}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #111827; background: #ffffff; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-size: 16px; margin-top: 32px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }}
  .meta {{ color: {NEUTRAL}; font-size: 13px; margin-bottom: 20px; }}
  .banner {{ border: 1px solid; border-radius: 6px; padding: 10px 14px; font-weight: 600; margin: 12px 0 20px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #f3f4f6; }}
  th {{ color: {NEUTRAL}; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  .email-cell {{ max-width: 220px; }}
  footer {{ margin-top: 40px; color: {NEUTRAL}; font-size: 12px; }}
</style>
</head>
<body>
  <h1>evalgate report</h1>
  <div class="meta">
    Prompt version: <strong>{current.prompt_version}</strong> &middot;
    Model: <strong>{current.model}</strong> &middot;
    Dataset: <strong>{current.dataset_version}</strong> &middot;
    Run time: {current.timestamp}
  </div>

  {status_banner}
  {_drift_banner(drift)}

  <h2>Scorecard</h2>
  <table>
    <thead><tr><th>Metric</th><th>Current</th><th>Baseline</th><th>Delta</th></tr></thead>
    <tbody>{scorecard}</tbody>
  </table>

  <h2>Regressions</h2>
  {regressions_html}

  <h2>All failing cases (this run)</h2>
  {_failures_table(current.results)}

  <h2>Pass rate trend</h2>
  {_trend_svg(history)}

  <footer>Generated by evalgate &middot; {len(history)} run(s) on record</footer>
</body>
</html>"""
