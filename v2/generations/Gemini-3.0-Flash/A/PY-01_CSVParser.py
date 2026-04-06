import csv
import io

def parse_csv(text: str) -> list[dict]:
    f = io.StringIO(text.strip())
    reader = csv.DictReader(f)
    return [row for row in reader]

if __name__ == "__main__":
    csv_text = """name,age,city
"Smith, John",30,New York
Jane,25,"Los Angeles, CA"
"""
    print(parse_csv(csv_text))
