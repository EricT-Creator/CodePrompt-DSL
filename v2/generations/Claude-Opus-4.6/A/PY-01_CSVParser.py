def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if not lines:
        return []
    headers = _parse_row(lines[0])
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = _parse_row(line)
        row = {}
        for i, header in enumerate(headers):
            row[header] = values[i] if i < len(values) else ""
        result.append(row)
    return result


def _parse_row(line: str) -> list[str]:
    fields = []
    current = []
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
