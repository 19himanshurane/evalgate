from src.models import CaseFlip, ComparisonResult, EvalRun, Severity

# "Is this delta signal or noise?" thresholds from the brief. These apply to
# DROPS in pass rate specifically -- an improvement is never something CI
# should block on, no matter how large.
WARNING_THRESHOLD = 0.03
CRITICAL_THRESHOLD = 0.08


def _severity(
    pass_rate_delta: float,
    warning_threshold: float = WARNING_THRESHOLD,
    critical_threshold: float = CRITICAL_THRESHOLD,
) -> Severity:
    if pass_rate_delta <= -critical_threshold:
        return "critical"
    if pass_rate_delta <= -warning_threshold:
        return "warning"
    if pass_rate_delta > 0:
        return "improved"
    return "ok"


def compare_runs(
    baseline: EvalRun,
    current: EvalRun,
    warning_threshold: float = WARNING_THRESHOLD,
    critical_threshold: float = CRITICAL_THRESHOLD,
) -> ComparisonResult:
    """Diffs two eval runs of the same golden dataset. Matches cases by ID,
    so this only makes sense when both runs used the same (or compatible)
    dataset version -- comparing across dataset versions would conflate
    'the prompt got worse' with 'the test data changed'."""
    baseline_by_id = {r.case_id: r for r in baseline.results}
    current_by_id = {r.case_id: r for r in current.results}
    shared_ids = set(baseline_by_id) & set(current_by_id)

    regressions = []
    improvements = []
    for case_id in shared_ids:
        b, c = baseline_by_id[case_id], current_by_id[case_id]
        if b.passed and not c.passed:
            regressions.append(
                CaseFlip(
                    case_id=case_id,
                    expected_category=b.expected_category,
                    baseline_predicted=b.predicted_category,
                    current_predicted=c.predicted_category,
                    baseline_summary_score=b.summary_score,
                    current_summary_score=c.summary_score,
                )
            )
        elif not b.passed and c.passed:
            improvements.append(
                CaseFlip(
                    case_id=case_id,
                    expected_category=b.expected_category,
                    baseline_predicted=b.predicted_category,
                    current_predicted=c.predicted_category,
                    baseline_summary_score=b.summary_score,
                    current_summary_score=c.summary_score,
                )
            )

    per_category_delta = {
        cat: current.per_category_accuracy.get(cat, 0.0) - acc
        for cat, acc in baseline.per_category_accuracy.items()
    }

    pass_rate_delta = current.pass_rate - baseline.pass_rate

    return ComparisonResult(
        baseline_version=baseline.prompt_version,
        current_version=current.prompt_version,
        baseline_timestamp=baseline.timestamp,
        current_timestamp=current.timestamp,
        pass_rate_delta=pass_rate_delta,
        per_category_accuracy_delta=per_category_delta,
        regressions=sorted(regressions, key=lambda f: f.case_id),
        improvements=sorted(improvements, key=lambda f: f.case_id),
        severity=_severity(pass_rate_delta, warning_threshold, critical_threshold),
    )
