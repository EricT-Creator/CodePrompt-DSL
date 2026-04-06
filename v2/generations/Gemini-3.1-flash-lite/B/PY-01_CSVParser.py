import csv
from io import StringIO

def parse_csv(text: str) -> list[dict]:
    # Constraint: { "language": "Python", "dependencies": "stdlib_only" }
    f = StringIO(text.strip())
    reader = csv.DictReader(f)
    return list(reader)
