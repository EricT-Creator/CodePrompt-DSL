import csv
import io


def parse_csv(text: str) -> list[dict]:
    """
    Parse CSV text (first row = header) into a list of dicts.
    Handles commas inside quotes. Uses only stdlib.
    
    Args:
        text: CSV formatted text string
        
    Returns:
        List of dictionaries where keys are column headers from first row
    """
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    return list(reader)
