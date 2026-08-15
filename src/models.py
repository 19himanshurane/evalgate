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
