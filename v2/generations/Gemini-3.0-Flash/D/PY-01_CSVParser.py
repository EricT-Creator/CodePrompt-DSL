import csv
import io

def parse_csv(文: str) -> list[dict]:
    流 = io.StringIO(文)
    读器 = csv.DictReader(流)
    return [行 for 行 in 读器]
