def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}
    
    def _flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}{separator}{i}" if prefix else str(i)
                _flatten(item, new_key)
        else:
            result[prefix] = obj
    
    _flatten(nested)
    return result
