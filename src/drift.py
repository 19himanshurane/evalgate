from src.models import DriftResult, EvalRun

DEFAULT_WINDOW = 7
DEFAULT_DRIFT_THRESHOLD = 0.05


def detect_drift(
    history: list[EvalRun],
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_DRIFT_THRESHOLD,
) -> DriftResult:
    """Computes a trailing moving average of pass rate at every point in
    history (using fewer runs than `window` at the start, once enough
    exist it's a true N-run trailing average), then compares the most
    recent moving average against the best one ever seen.

    Per-run diffs (compare_runs) only ever look at two adjacent runs, so a
    prompt that erodes by 1% every run for ten runs straight never trips a
    single "warning" -- each step is noise-sized on its own. This looks at
    the trend instead, which is where that kind of slow bleed shows up.
    """
    pass_rates = [r.pass_rate for r in history]
    moving_avgs = []
    for i in range(len(pass_rates)):
        chunk = pass_rates[max(0, i - window + 1) : i + 1]
        moving_avgs.append(sum(chunk) / len(chunk))

    current_ma = moving_avgs[-1]
    best_ma = max(moving_avgs)
    drift = best_ma - current_ma

    return DriftResult(
        window=window,
        current_moving_avg=current_ma,
        best_moving_avg=best_ma,
        drift=drift,
        is_drifting=drift >= threshold,
    )
