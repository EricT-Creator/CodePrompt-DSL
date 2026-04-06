def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}
    
    def _flatten(obj, prefix=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                new_key = f"{prefix}{separator}{index}" if prefix else str(index)
                _flatten(value, new_key)
        else:
            result[prefix] = obj
    
    _flatten(nested)
    return result
