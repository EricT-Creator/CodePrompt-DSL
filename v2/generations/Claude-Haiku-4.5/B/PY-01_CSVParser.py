def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split('\n')
    if not lines:
        return []
    
    header = _parse_csv_line(lines[0])
    result = []
    
    for line in lines[1:]:
        if line.strip():
            values = _parse_csv_line(line)
            result.append(dict(zip(header, values)))
    
    return result

def _parse_csv_line(line: str) -> list[str]:
    values = []
    current = ""
    in_quotes = False
    i = 0
    
    while i < len(line):
        char = line[i]
        
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            values.append(current.strip())
            current = ""
        else:
            current += char
        
        i += 1
    
    values.append(current.strip())
    return values
