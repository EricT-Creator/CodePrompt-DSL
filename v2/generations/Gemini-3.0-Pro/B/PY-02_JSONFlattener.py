def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}

    def _flatten(obj, parent_key=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                _flatten(value, new_key)
        else:
            result[parent_key] = obj

    _flatten(nested)
    return result
