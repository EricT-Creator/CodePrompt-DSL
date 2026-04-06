import csv
import io
from typing import List, Dict

def parse_csv(csv_text: str) -> List[Dict[str, str]]:
    if not csv_text.strip():
        return []
    
    csv_file = io.StringIO(csv_text.strip())
    reader = csv.DictReader(csv_file)
    return list(reader)
