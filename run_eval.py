"""Runs the golden dataset against a prompt version and saves the result.

Run: python run_eval.py [--prompt prompts/email_classifier_v1.yaml] [--dataset data/golden_dataset_v1.json]
"""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.classifier import load_prompt_config
from src.dataset import load_golden_dataset
from src.evaluator import run_eval


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="prompts/email_classifier_v1.yaml")
    parser.add_argument("--dataset", default="data/golden_dataset_v1.json")
    args = parser.parse_args()

    config = load_prompt_config(args.prompt)
    dataset = load_golden_dataset(args.dataset)

    print(f"Running eval: prompt={config.version} model={config.model} cases={len(dataset.cases)}\n")
    eval_run = await run_eval(config, dataset)

    print(f"Pass rate:           {eval_run.pass_rate:.1%}")
    print(f"Category accuracy:   {eval_run.category_accuracy:.1%}")
    print(f"Avg summary score:   {eval_run.avg_summary_score:.2f}/5")
    print(f"Avg latency:         {eval_run.avg_latency_ms:.0f}ms")
    print(f"Total tokens:        {eval_run.total_tokens}")

    print("\nPer-category accuracy:")
    for cat, acc in sorted(eval_run.per_category_accuracy.items()):
        print(f"  {cat:10s} {acc:.1%}")

    failures = [r for r in eval_run.results if not r.passed]
    print(f"\n{len(failures)} failing case(s):")
    for r in failures:
        reason = "category" if not r.category_correct else "summary"
        print(
            f"  {r.case_id} [{reason}] expected={r.expected_category} "
            f"predicted={r.predicted_category} summary_score={r.summary_score}"
        )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"runs/{config.version}_{run_id}.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(eval_run.model_dump_json(indent=2))
    print(f"\nSaved run to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
