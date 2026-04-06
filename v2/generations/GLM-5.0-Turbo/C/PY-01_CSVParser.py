def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if not lines:
        return []
    keys = _parse_fields(lines[0])
    return [{keys[j]: vals[j] if j < len(vals) else "" for j in range(len(keys))}
            for vals in (_parse_fields(l) for l in lines[1:])]


def _parse_fields(row: str) -> list[str]:
    result, field, q = [], [], False
    for i, c in enumerate(row):
        if q:
            if c == '"' and row[i + 1:i + 2] == '"':
                field.append('"')
            elif c == '"':
                q = False
            else:
                field.append(c)
        elif c == '"':
            q = True
        elif c == ',':
            result.append("".join(field))
            field = []
        else:
            field.append(c)
    result.append("".join(field))
    return result
