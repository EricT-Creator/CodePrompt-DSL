import re
from typing import Optional


def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return []
    headers = _split_csv_line(lines[0])
    result = []
    for line in lines[1:]:
        values = _split_csv_line(line)
        row = {}
        for i, header in enumerate(headers):
            row[header] = values[i] if i < len(values) else ""
        result.append(row)
    return result


def _split_csv_line(line: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    current.append('"')
                    i += 2
                    continue
                else:
                    in_quotes = False
            else:
                current.append(ch)
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ',':
                fields.append("".join(current))
                current = []
            else:
                current.append(ch)
        i += 1
    fields.append("".join(current))
    return fields
