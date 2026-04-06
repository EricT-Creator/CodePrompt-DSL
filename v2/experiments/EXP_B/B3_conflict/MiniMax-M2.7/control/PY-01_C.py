import csv
from io import StringIO

def parse_csv(text: str) -> list[dict]:
    """
    Parse CSV text (first row = header) into a list of dicts.
    Handles commas inside quotes. Uses only stdlib.
    """
    reader = csv.DictReader(StringIO(text.strip()), restkey=None, restval=None)
    return list(reader)
