def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if not lines:
        return []
    headers = lines[0].split(",")
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = []
        in_quote = False
        current = ""
        for char in line:
            if char == '"':
                in_quote = not in_quote
            elif char == "," and not in_quote:
                fields.append(current.strip('"'))
                current = ""
            else:
                current += char
        fields.append(current.strip('"'))
        row = {}
        for h, f in zip(headers, fields):
            row[h.strip()] = f.strip() if f.strip().lower() not in ("", "null", "none") else ""
        result.append(row)
    return result