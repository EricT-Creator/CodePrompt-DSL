import csv
import io

def parse_csv(text: str) -> list[dict]:
    """Parse CSV text into list of dictionaries"""
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)

# Example usage:
if __name__ == "__main__":
    csv_text = """name,age,city
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,35,Chicago"""
    result = parse_csv(csv_text)
    print(result)