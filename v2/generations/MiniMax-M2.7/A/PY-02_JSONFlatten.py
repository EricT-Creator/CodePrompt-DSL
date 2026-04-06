def flatten_json(nested: dict, separator: str = ".") -> dict:
    result = {}
    def _flatten(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _flatten(v, prefix + separator + k if prefix else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _flatten(v, prefix + separator + str(i))
        else:
            result[prefix] = obj
    _flatten(nested, "")
    return result