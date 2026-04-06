def flatten_json(nested: dict, separator: str = ".") -> dict:
    flat = {}
    def _go(val, key):
        if isinstance(val, dict):
            for k, v in val.items():
                _go(v, f"{key}{separator}{k}" if key else k)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                _go(v, f"{key}{separator}{i}" if key else str(i))
        else:
            flat[key] = val
    _go(nested, "")
    return flat
