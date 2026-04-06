def flatten_json(nested: dict, separator: str = ".") -> dict:
    output: dict[str, object] = {}
    stack: list[tuple[str, object]] = [("", nested)]
    while stack:
        prefix, value = stack.pop()
        if isinstance(value, dict):
            items = list(value.items())
            for key, child in reversed(items):
                next_prefix = f"{prefix}{separator}{key}" if prefix else str(key)
                stack.append((next_prefix, child))
        elif isinstance(value, list):
            for index in range(len(value) - 1, -1, -1):
                child = value[index]
                next_prefix = f"{prefix}{separator}{index}" if prefix else str(index)
                stack.append((next_prefix, child))
        else:
            output[prefix] = value
    return output
