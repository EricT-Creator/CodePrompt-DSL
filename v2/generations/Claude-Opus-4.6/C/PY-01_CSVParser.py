def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if not lines:
        return []
    headers = _tokenize(lines[0])
    output = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        vals = _tokenize(line)
        entry = {headers[j]: (vals[j] if j < len(vals) else "") for j in range(len(headers))}
        output.append(entry)
    return output


def _tokenize(raw: str) -> list[str]:
    tokens = []
    acc = []
    inside = False
    idx = 0
    while idx < len(raw):
        char = raw[idx]
        if inside:
            if char == '"':
                if idx + 1 < len(raw) and raw[idx + 1] == '"':
                    acc.append('"')
                    idx += 2
                    continue
                inside = False
            else:
                acc.append(char)
        elif char == '"':
            inside = True
        elif char == ',':
            tokens.append("".join(acc))
            acc = []
        else:
            acc.append(char)
        idx += 1
    tokens.append("".join(acc))
    return tokens
