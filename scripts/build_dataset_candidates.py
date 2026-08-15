"""One-time script: builds SCENARIO PROMPTS (not fake emails) from the
Kaggle CSV and writes them into data/golden_dataset_v1.json as EDITABLE
CANDIDATES.

The raw 'Ticket Description' text in this dataset is broken (garbled
template concatenation, see project notes), so it is not used at all.
Instead each candidate is built from three clean, reliable fields:
Ticket Type (mapped to our category), Product Purchased, and Ticket
Subject (16 fixed short phrases, e.g. "Battery life", "Account access").

This does NOT produce a finished golden dataset. Every case still needs
a human pass: write an actual email for the given scenario, confirm/fix
the category, write the summary, and set a real difficulty. That review
step is what makes the final dataset "hand-verified."

Run: python scripts/build_dataset_candidates.py
"""

import csv
import json
import random

RAW_CSV = "data/raw/customer_support_tickets.csv"
OUT_PATH = "data/golden_dataset_v1.json"
SEED = 42

# Kaggle's 5 ticket types mapped to our 4 categories. Cancellation request
# maps to "account" (it's a plan/account-state change), Refund request
# maps to "billing" (it's fundamentally a money question), same reasoning
# we used for tc-033 in the earlier draft.
TYPE_TO_CATEGORY = {
    "Technical issue": "technical",
    "Billing inquiry": "billing",
    "Refund request": "billing",
    "Cancellation request": "account",
    "Product inquiry": "general",
}

# How many raw candidates to pull per ticket type, chosen so the 4 final
# categories end up roughly balanced (billing gets two source types).
SAMPLE_COUNTS = {
    "Technical issue": 12,
    "Cancellation request": 12,
    "Product inquiry": 12,
    "Billing inquiry": 7,
    "Refund request": 7,
}


def main() -> None:
    random.seed(SEED)

    with open(RAW_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_type: dict[str, list[dict]] = {}
    for row in rows:
        by_type.setdefault(row["Ticket Type"], []).append(row)

    cases = []
    case_num = 1
    for ticket_type, count in SAMPLE_COUNTS.items():
        candidates = by_type[ticket_type]
        random.shuffle(candidates)

        seen_combos: set[tuple[str, str]] = set()
        picked = []
        for row in candidates:
            combo = (row["Ticket Subject"], row["Product Purchased"])
            if combo in seen_combos:
                continue
            seen_combos.add(combo)
            picked.append(row)
            if len(picked) == count:
                break

        for row in picked:
            product = row["Product Purchased"]
            subject = row["Ticket Subject"]
            priority = row["Ticket Priority"]

            cases.append(
                {
                    "id": f"tc-{case_num:03d}",
                    "email": (
                        f"[WRITE YOUR OWN EMAIL] Scenario: a customer with a "
                        f"'{subject}' issue involving their {product}."
                    ),
                    "expected_category": TYPE_TO_CATEGORY[ticket_type],
                    "expected_summary": "WRITE YOUR OWN SUMMARY HERE",
                    "difficulty": "easy",
                    "notes": (
                        f"Inspired by Kaggle ticket #{row['Ticket ID']} -- "
                        f"type='{ticket_type}', subject='{subject}', "
                        f"product='{product}', original priority='{priority}'. "
                        f"The raw description text was discarded (broken/garbled), "
                        f"so write a fresh, original email for this scenario. Confirm "
                        f"or change the category (currently auto-mapped from "
                        f"'{ticket_type}'). Write your own summary and difficulty."
                    ),
                }
            )
            case_num += 1

    dataset = {
        "version": "v1",
        "created_at": "2026-08-15T00:00:00Z",
        "cases": cases,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(cases)} candidate scenarios to {OUT_PATH}")
    print("Every case still needs your review pass -- see the 'notes' field on each.")


if __name__ == "__main__":
    main()
