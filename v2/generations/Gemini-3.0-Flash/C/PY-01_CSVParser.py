import csv
import io

def parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))
