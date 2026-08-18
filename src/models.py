from typing import Literal
from pydantic import BaseModel, Field

Category = Literal["billing", "technical", "account", "general"]


class FewShotExample(BaseModel):
    email: str
    category: Category
    summary: str


class PromptConfig(BaseModel):
    """The versioned 'code' the eval pipeline runs against.

    Loaded straight from a /prompts/*.yaml file. Anything that changes
    model behavior (prompt text, few-shot examples, model name,
    temperature) must live here, not be hardcoded in the classifier.
    """

    version: str
    created_at: str
    model: str
    temperature: float = 0.0
    system_prompt: str
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)


class EmailClassification(BaseModel):
    """The structured output contract for the classifier."""

    category: Category
    summary: str


Difficulty = Literal["easy", "medium", "hard"]


class TestCase(BaseModel):
    """One hand-labeled example in the golden dataset."""

    id: str
    email: str
    expected_category: Category
    expected_summary: str
    difficulty: Difficulty
    notes: str


class GoldenDataset(BaseModel):
    """The versioned ground truth the eval pipeline scores every run against."""

    version: str
    created_at: str
    cases: list[TestCase]


class JudgeScore(BaseModel):
    """LLM-as-judge output: how well the predicted summary matches the
    expected one, on a 1-5 scale, with a one-line reason."""

    score: int = Field(ge=1, le=5)
    reasoning: str


class CaseResult(BaseModel):
    """One test case's outcome for a single eval run."""

    case_id: str
    difficulty: Difficulty
    expected_category: Category
    predicted_category: Category
    category_correct: bool
    expected_summary: str
    predicted_summary: str
    summary_score: int
    judge_reasoning: str
    passed: bool
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int


class EvalRun(BaseModel):
    """A full run of the golden dataset against one prompt version --
    this is what gets diffed against the previous run in Phase 3's
    comparison logic, and what gets saved to /runs as a permanent record."""

    prompt_version: str
    model: str
    dataset_version: str
    timestamp: str
    results: list[CaseResult]

    total_cases: int
    category_accuracy: float
    pass_rate: float
    avg_summary_score: float
    avg_latency_ms: float
    total_tokens: int
    per_category_accuracy: dict[str, float]


class CaseFlip(BaseModel):
    """A single case whose pass/fail outcome changed between two runs."""

    case_id: str
    expected_category: Category
    baseline_predicted: Category
    current_predicted: Category
    baseline_summary_score: int
    current_summary_score: int


Severity = Literal["critical", "warning", "ok", "improved"]


class ComparisonResult(BaseModel):
    """The diff between a baseline run and a current run -- the core value
    of the whole system: not 'what's the score' but 'what changed'."""

    baseline_version: str
    current_version: str
    baseline_timestamp: str
    current_timestamp: str

    pass_rate_delta: float
    per_category_accuracy_delta: dict[str, float]
    regressions: list[CaseFlip]
    improvements: list[CaseFlip]
    severity: Severity


class DriftResult(BaseModel):
    """Rolling-average check across many runs -- catches gradual decline
    that no single run-over-run diff would trigger, since each individual
    step might be too small to flag on its own."""

    window: int
    current_moving_avg: float
    best_moving_avg: float
    drift: float
    is_drifting: bool
