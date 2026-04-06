import re
from typing import List, Dict


def parse_csv(text: str) -> List[Dict[str, str]]:
    rows = text.strip().splitlines()
    if not rows:
        return []
    header_row = _tokenize(rows[0])
    output = []
    for raw_row in rows[1:]:
        cells = _tokenize(raw_row)
        record = {}
        for idx, col_name in enumerate(header_row):
            record[col_name] = cells[idx] if idx < len(cells) else ""
        output.append(record)
    return output


def _tokenize(line: str) -> List[str]:
    tokens: List[str] = []
    buf: List[str] = []
    quoted = False
    pos = 0
    while pos < len(line):
        c = line[pos]
        if quoted:
            if c == '"':
                if pos + 1 < len(line) and line[pos + 1] == '"':
                    buf.append('"')
                    pos += 2
                    continue
                quoted = False
            else:
                buf.append(c)
        elif c == '"':
            quoted = True
        elif c == ',':
            tokens.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        pos += 1
    tokens.append("".join(buf))
    return tokens
