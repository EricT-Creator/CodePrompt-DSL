import csv
from io import StringIO


def parse_csv(text: str) -> list[dict]:
    stripped = text.strip("\n")
    if not stripped:
        return []
    reader = csv.DictReader(StringIO(stripped), skipinitialspace=False)
    records: list[dict] = []
    for row in reader:
        records.append({key: value for key, value in row.items()})
    return records
