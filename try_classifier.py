"""Manual smoke test for Phase 1 — not part of the eval pipeline.

Run: python try_classifier.py
"""

from dotenv import load_dotenv

from src.classifier import active_prompt_path, classify_email, get_client, load_prompt_config

load_dotenv()

SAMPLE_EMAILS = [
    "I was billed $49.99 but I cancelled my plan last week. Please refund me.",
    "Every time I click 'export', the app just freezes. Please help!",
    "hey can u reset my pw i forgot it lol",
    "Do you offer discounts for non-profits?",
]


def main() -> None:
    config = load_prompt_config(active_prompt_path())
    client = get_client()

    print(f"Using prompt version: {config.version} ({config.model})\n")

    for email in SAMPLE_EMAILS:
        result = classify_email(email, config, client)
        print(f"EMAIL:    {email}")
        print(f"CATEGORY: {result.category}")
        print(f"SUMMARY:  {result.summary}")
        print(f"LATENCY:  {result.latency_ms:.0f}ms | tokens: {result.prompt_tokens}+{result.completion_tokens}")
        print("-" * 60)


if __name__ == "__main__":
    main()
