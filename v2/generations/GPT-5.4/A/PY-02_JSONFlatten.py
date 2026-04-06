def flatten_json(nested: dict, separator: str = ".") -> dict:
    flat: dict[str, object] = {}

    def visit(value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                next_prefix = f"{prefix}{separator}{key}" if prefix else str(key)
                visit(child, next_prefix)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                next_prefix = f"{prefix}{separator}{index}" if prefix else str(index)
                visit(child, next_prefix)
        else:
            flat[prefix] = value

    visit(nested)
    return flat
