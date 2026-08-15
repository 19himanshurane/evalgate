import json
from pathlib import Path

from src.models import GoldenDataset


def load_golden_dataset(path: str | Path) -> GoldenDataset:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return GoldenDataset(**raw)
