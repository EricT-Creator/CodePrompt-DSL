import csv
from typing import Any


def parse_csv(filepath: str) -> list[dict[str, Any]]:
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]
