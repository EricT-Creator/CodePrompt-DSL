import csv
import io
from typing import List, Dict

def parse_csv(text: str) -> List[Dict[str, str]]:
    if not text.strip():
        return []
    
    file_like = io.StringIO(text.strip())
    reader = csv.DictReader(file_like)
    return list(reader)
