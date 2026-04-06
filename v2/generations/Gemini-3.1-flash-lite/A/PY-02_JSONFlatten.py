def flatten_json(nested: dict, separator: str = ".") -> dict:
    out = {}
    def recurse(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recurse(v, f"{prefix}{k}{separator}" if prefix else f"{k}{separator}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                recurse(v, f"{prefix}{i}{separator}")
        else:
            out[prefix.rstrip(separator)] = obj
    recurse(nested)
    return out
