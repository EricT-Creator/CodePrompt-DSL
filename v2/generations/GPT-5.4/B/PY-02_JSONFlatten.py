def flatten_json(nested: dict, separator: str = ".") -> dict:
    result: dict[str, object] = {}

    def walk(value: object, parts: list[str]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, parts + [str(key)])
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, parts + [str(index)])
            return
        result[separator.join(parts)] = value

    walk(nested, [])
    return result
