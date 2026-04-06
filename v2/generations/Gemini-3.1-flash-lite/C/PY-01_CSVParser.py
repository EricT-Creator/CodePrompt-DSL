import csv
from io import StringIO

# [L]Py[F]None[D]StdLib
def parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(StringIO(text.strip())))
