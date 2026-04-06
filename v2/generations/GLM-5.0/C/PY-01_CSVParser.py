import csv
import io
from typing import List, Dict

def parse_csv(text: str) -> List[Dict[str, str]]:
    result = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        result.append(dict(row))
    return result