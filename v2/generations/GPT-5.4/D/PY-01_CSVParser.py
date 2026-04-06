import csv
from io import StringIO


def parse_csv(text: str) -> list[dict]:
    source = text.strip()
    if not source:
        return []
    data = StringIO(source)
    reader = csv.reader(data)
    headers = next(reader, [])
    result: list[dict] = []
    for row in reader:
        values = row + [""] * max(0, len(headers) - len(row))
        result.append({headers[index]: values[index] for index in range(len(headers))})
    return result
