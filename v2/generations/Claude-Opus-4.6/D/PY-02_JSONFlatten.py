def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}
    stack = [("", nested)]
    while stack:
        prefix, current = stack.pop()
        if isinstance(current, dict):
            for k, v in current.items():
                full_key = f"{prefix}{separator}{k}" if prefix else k
                stack.append((full_key, v))
        elif isinstance(current, list):
            for i, v in enumerate(current):
                full_key = f"{prefix}{separator}{i}" if prefix else str(i)
                stack.append((full_key, v))
        else:
            result[prefix] = current
    return result
