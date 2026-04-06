import csv
from io import StringIO


def parse_csv(text: str) -> list[dict]:
    if not text.strip():
        return []
    stream = StringIO(text)
    rows = csv.reader(stream)
    header = next(rows, None)
    if not header:
        return []
    return [dict(zip(header, row)) for row in rows]
