def parse_csv(text: str) -> list[dict]:
    rows = text.strip().splitlines()
    if len(rows) < 1:
        return []
    header = _split_csv_line(rows[0])
    records = []
    for row in rows[1:]:
        stripped = row.strip()
        if not stripped:
            continue
        values = _split_csv_line(stripped)
        record = {}
        for idx, col in enumerate(header):
            record[col] = values[idx] if idx < len(values) else ""
        records.append(record)
    return records


def _split_csv_line(line: str) -> list[str]:
    result = []
    buf = []
    quoted = False
    pos = 0
    while pos < len(line):
        c = line[pos]
        if quoted:
            if c == '"':
                if pos + 1 < len(line) and line[pos + 1] == '"':
                    buf.append('"')
                    pos += 1
                else:
                    quoted = False
            else:
                buf.append(c)
        elif c == '"':
            quoted = True
        elif c == ',':
            result.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        pos += 1
    result.append("".join(buf))
    return result
