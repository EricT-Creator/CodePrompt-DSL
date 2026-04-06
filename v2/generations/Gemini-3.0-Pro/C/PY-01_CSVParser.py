import csv
from io import StringIO
from typing import List, Dict

def parse_csv(csv_string: str) -> List[Dict[str, str]]:
    if not csv_string.strip():
        return []
        
    f = StringIO(csv_string.strip())
    reader = csv.DictReader(f)
    return list(reader)
