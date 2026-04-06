import csv
from io import StringIO


def parse_csv(text: str) -> list[dict]:
    if not text.strip():
        return []
    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]
