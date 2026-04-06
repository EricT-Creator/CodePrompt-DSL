import csv
from io import StringIO

def parse_csv(text: str) -> list[dict]:
    f = StringIO(text.strip())
    reader = csv.DictReader(f)
    return [row for row in reader]
