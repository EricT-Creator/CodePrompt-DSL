def parse_csv(text: str) -> list[dict]:
    lines = text.strip().splitlines()
    if len(lines) < 1:
        return []
    columns = _split_line(lines[0])
    data = []
    for line in lines[1:]:
        values = _split_line(line)
        row_dict = {}
        for col_idx, col_name in enumerate(columns):
            row_dict[col_name] = values[col_idx] if col_idx < len(values) else ""
        data.append(row_dict)
    return data


def _split_line(line: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quote:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    current.append('"')
                    i += 2
                    continue
                in_quote = False
            else:
                current.append(ch)
        elif ch == '"':
            in_quote = True
        elif ch == ',':
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts
