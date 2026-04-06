def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split('\n')
    if not lines:
        return []
    
    headers = []
    in_quotes = False
    current_field = ''
    
    for char in lines[0]:
        if char == '"':
            in_quotes = not in_quotes
            current_field += char
        elif char == ',' and not in_quotes:
            headers.append(current_field.strip().strip('"'))
            current_field = ''
        else:
            current_field += char
    headers.append(current_field.strip().strip('"'))
    
    result = []
    for line in lines[1:]:
        row = {}
        fields = []
        in_quotes = False
        current_field = ''
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
                current_field += char
            elif char == ',' and not in_quotes:
                fields.append(current_field.strip().strip('"'))
                current_field = ''
            else:
                current_field += char
        fields.append(current_field.strip().strip('"'))
        
        for i, header in enumerate(headers):
            row[header] = fields[i] if i < len(fields) else ''
        result.append(row)
    
    return result
