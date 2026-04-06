def parse_csv(text: str) -> list[dict]:
    all_lines = text.strip().split("\n")
    if not all_lines:
        return []
    col_names = _read_fields(all_lines[0])
    data = []
    for raw in all_lines[1:]:
        raw = raw.strip()
        if not raw:
            continue
        field_vals = _read_fields(raw)
        row_dict = {}
        for k in range(len(col_names)):
            row_dict[col_names[k]] = field_vals[k] if k < len(field_vals) else ""
        data.append(row_dict)
    return data


def _read_fields(line: str) -> list[str]:
    fields = []
    tmp = []
    q = False
    p = 0
    while p < len(line):
        ch = line[p]
        if q:
            if ch == '"':
                if p + 1 < len(line) and line[p + 1] == '"':
                    tmp.append('"')
                    p += 2
                    continue
                q = False
            else:
                tmp.append(ch)
        elif ch == '"':
            q = True
        elif ch == ',':
            fields.append("".join(tmp))
            tmp = []
        else:
            tmp.append(ch)
        p += 1
    fields.append("".join(tmp))
    return fields
