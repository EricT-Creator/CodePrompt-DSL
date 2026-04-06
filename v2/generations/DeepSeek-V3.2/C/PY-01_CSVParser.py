import csv
from io import StringIO
from typing import List, Dict

def parse_csv(text: str) -> List[Dict[str, str]]:
    """
    Parse a CSV format string (first row is header) into a list of dictionaries.
    Handles commas inside quoted fields correctly.
    
    Args:
        text: CSV format string with header row
        
    Returns:
        List of dictionaries where keys are header values
    """
    if not text.strip():
        return []
    
    reader = csv.DictReader(StringIO(text))
    result = []
    for row in reader:
        result.append(dict(row))
    return result