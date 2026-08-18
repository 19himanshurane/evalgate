import asyncio
from datetime import datetime, timezone

from openai import AsyncOpenAI, RateLimitError

from src.classifier import ClassificationResult, classify_email_async, get_async_client
from src.models import CaseResult, EvalRun, GoldenDataset, JudgeScore, PromptConfig, TestCase

# A separate, stronger model does the judging, on purpose -- if the same
# model graded its own homework, systematic biases in that model would go
# undetected. Using a different model is a cheap way to reduce that risk.
JUDGE_MODEL = "openai/gpt-oss-120b"

SUMMARY_SCORE_PASS_THRESHOLD = 3
# Groq's free tier caps tokens-per-minute (not just requests-per-minute),
# so low concurrency + honoring the API's own retry-after hint matters more
# here than it would against a paid tier.
CONCURRENCY = 2
MAX_RETRIES = 10

JUDGE_SYSTEM_PROMPT = """You are grading an AI-generated email summary against a \
human-written reference summary. Score how well the AI summary captures the \
same core request as the reference, on a 1-5 scale:
  5 = captures the same core request, no meaningful loss of information
  3 = captures the general gist but misses a meaningful detail
  1 = misses or misrepresents the core request entirely
Judge meaning, not wording -- a differently-phrased summary that captures the \
same request should still score 5."""


async def _with_retry(coro_fn, *args, **kwargs):
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        try:
            return await coro_fn(*args, **kwargs)
        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            # Prefer the API's own retry-after hint over blind backoff.
            retry_after = None
            try:
                retry_after = float(e.response.headers.get("retry-after"))
            except (AttributeError, TypeError, ValueError):
                pass
            await asyncio.sleep(retry_after if retry_after else delay)
            delay = min(delay * 2, 30.0)


async def judge_summary(
    email: str, expected_summary: str, predicted_summary: str, client: AsyncOpenAI
) -> JudgeScore:
    completion = await client.beta.chat.completions.parse(
        model=JUDGE_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original email:\n{email}\n\n"
                    f"Reference summary:\n{expected_summary}\n\n"
                    f"AI-generated summary:\n{predicted_summary}"
                ),
            },
        ],
        response_format=JudgeScore,
    )
    return completion.choices[0].message.parsed


async def evaluate_case(
    case: TestCase,
    config: PromptConfig,
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
) -> CaseResult:
    async with semaphore:
        classification: ClassificationResult = await _with_retry(
            classify_email_async, case.email, config, client
        )
        judged: JudgeScore = await _with_retry(
            judge_summary, case.email, case.expected_summary, classification.summary, client
        )

    category_correct = classification.category == case.expected_category
    passed = category_correct and judged.score >= SUMMARY_SCORE_PASS_THRESHOLD

    return CaseResult(
        case_id=case.id,
        difficulty=case.difficulty,
        expected_category=case.expected_category,
        predicted_category=classification.category,
        category_correct=category_correct,
        expected_summary=case.expected_summary,
        predicted_summary=classification.summary,
        summary_score=judged.score,
        judge_reasoning=judged.reasoning,
        passed=passed,
        latency_ms=classification.latency_ms,
        prompt_tokens=classification.prompt_tokens,
        completion_tokens=classification.completion_tokens,
    )


def _aggregate(config: PromptConfig, dataset: GoldenDataset, results: list[CaseResult]) -> EvalRun:
    n = len(results)
    by_category: dict[str, list[CaseResult]] = {}
    for r in results:
        by_category.setdefault(r.expected_category, []).append(r)

    per_category_accuracy = {
        cat: sum(r.category_correct for r in rs) / len(rs) for cat, rs in by_category.items()
    }

    return EvalRun(
        prompt_version=config.version,
        model=config.model,
        dataset_version=dataset.version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        total_cases=n,
        category_accuracy=sum(r.category_correct for r in results) / n,
        pass_rate=sum(r.passed for r in results) / n,
        avg_summary_score=sum(r.summary_score for r in results) / n,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        total_tokens=sum(r.prompt_tokens + r.completion_tokens for r in results),
        per_category_accuracy=per_category_accuracy,
    )


def load_eval_run(path: str) -> EvalRun:
    with open(path, "r", encoding="utf-8") as f:
        return EvalRun.model_validate_json(f.read())


async def run_eval(config: PromptConfig, dataset: GoldenDataset) -> EvalRun:
    """Runs every case in the golden dataset through the classifier under
    test, concurrently (bounded by CONCURRENCY), scores each one, and
    returns the aggregated run."""
    client = get_async_client()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    results = await asyncio.gather(
        *(evaluate_case(case, config, client, semaphore) for case in dataset.cases)
    )
    return _aggregate(config, dataset, list(results))
