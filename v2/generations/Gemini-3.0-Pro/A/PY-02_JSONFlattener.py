def flatten_json(nested: dict, separator: str = ".") -> dict:
    flattened = {}

    def _flatten(obj, parent_key=''):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{parent_key}{separator}{k}" if parent_key else k
                _flatten(v, new_key)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                _flatten(v, new_key)
        else:
            flattened[parent_key] = obj

    _flatten(nested)
    return flattened
