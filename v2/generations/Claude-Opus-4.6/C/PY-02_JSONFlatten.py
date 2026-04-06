def flatten_json(nested: dict, separator: str = ".") -> dict:
    flat = {}

    def recurse(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_prefix = f"{prefix}{separator}{k}" if prefix else k
                recurse(v, new_prefix)
        elif isinstance(obj, list):
            for idx, v in enumerate(obj):
                new_prefix = f"{prefix}{separator}{idx}" if prefix else str(idx)
                recurse(v, new_prefix)
        else:
            flat[prefix] = obj

    recurse(nested, "")
    return flat
