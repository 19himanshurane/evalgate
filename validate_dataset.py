"""Run this anytime while filling in the golden dataset to check your progress.

Run: python validate_dataset.py
"""

from collections import Counter

from pydantic import ValidationError

from src.dataset import load_golden_dataset

PATH = "data/golden_dataset_v1.json"
TARGET_MIN = 50
TARGET_MAX = 100


def main() -> None:
    try:
        dataset = load_golden_dataset(PATH)
    except ValidationError as e:
        print("Schema errors -- fix these first:\n")
        print(e)
        return

    cases = dataset.cases
    ids = [c.id for c in cases]
    duplicates = [id_ for id_, count in Counter(ids).items() if count > 1]

    print(f"Total cases: {len(cases)} (target: {TARGET_MIN}-{TARGET_MAX})")
    print(f"By category: {dict(Counter(c.expected_category for c in cases))}")
    print(f"By difficulty: {dict(Counter(c.difficulty for c in cases))}")

    if duplicates:
        print(f"\nDUPLICATE IDs found: {duplicates}")

    placeholders = [
        c.id
        for c in cases
        if "PASTE OR WRITE" in c.email
        or "WRITE YOUR OWN EMAIL" in c.email
        or "WRITE YOUR OWN SUMMARY" in c.expected_summary
    ]
    if placeholders:
        print(f"\nStill-placeholder cases (not yet written): {placeholders}")

    if len(cases) < TARGET_MIN:
        print(f"\n{TARGET_MIN - len(cases)} more cases to go to hit the minimum target.")
    elif not duplicates and not placeholders:
        print("\nLooks good.")


if __name__ == "__main__":
    main()
