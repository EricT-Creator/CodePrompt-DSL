import csv
import io
from typing import List, Dict

def parse_csv(text: str) -> List[Dict[str, str]]:
    if not text.strip():
        return []
        
    f = io.StringIO(text.strip())
    reader = csv.DictReader(f)
    return list(reader)
