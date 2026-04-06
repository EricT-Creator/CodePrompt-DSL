def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}
    _flatten(nested, "", separator, result)
    return result


def _flatten(obj, prefix: str, sep: str, out: dict):
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}{sep}{key}" if prefix else key
            _flatten(value, new_key, sep, out)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            new_key = f"{prefix}{sep}{index}" if prefix else str(index)
            _flatten(value, new_key, sep, out)
    else:
        out[prefix] = obj
