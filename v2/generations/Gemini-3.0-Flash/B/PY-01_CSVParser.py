import csv
import io

def parse_csv(text: str) -> list[dict]:
    f = io.StringIO(text)
    reader = csv.DictReader(f, skipinitialspace=True)
    return list(reader)
