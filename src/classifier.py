import json
import os
import time
from pathlib import Path

import yaml
from openai import OpenAI

from src.models import EmailClassification, PromptConfig

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_client() -> OpenAI:
    """Groq exposes an OpenAI-compatible API — same SDK, different base_url/key."""
    return OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url=GROQ_BASE_URL)


def load_prompt_config(path: str | Path) -> PromptConfig:
    """Load and validate a versioned prompt file from /prompts."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return PromptConfig(**raw)


def _build_messages(config: PromptConfig, email_text: str) -> list[dict]:
    messages = [{"role": "system", "content": config.system_prompt}]

    for ex in config.few_shot_examples:
        messages.append({"role": "user", "content": ex.email})
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {"category": ex.category, "summary": ex.summary}
                ),
            }
        )

    messages.append({"role": "user", "content": email_text})
    return messages


class ClassificationResult(EmailClassification):
    """Classification output plus the metadata an eval run needs to score it."""

    latency_ms: float
    prompt_tokens: int
    completion_tokens: int


def classify_email(
    email_text: str, config: PromptConfig, client: OpenAI
) -> ClassificationResult:
    """Run one email through the classifier feature under test.

    This is the single function the eval pipeline calls per test case —
    everything that affects behavior (prompt text, few-shots, model,
    temperature) comes in through `config`, never hardcoded here.
    """
    messages = _build_messages(config, email_text)

    start = time.perf_counter()
    completion = client.beta.chat.completions.parse(
        model=config.model,
        temperature=config.temperature,
        messages=messages,
        response_format=EmailClassification,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    parsed = completion.choices[0].message.parsed
    usage = completion.usage

    return ClassificationResult(
        category=parsed.category,
        summary=parsed.summary,
        latency_ms=latency_ms,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )
