import csv

def parse_csv(filepath: str) -> list[dict]:
    """
    Read a CSV file and return a list of dictionaries.
    Each dictionary represents a row, keyed by column headers.
    """
    rows = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
