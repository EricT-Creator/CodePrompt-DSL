def flatten_json(nested: dict, separator: str = ".") -> dict:
    # Constraint: { "dependencies": "stdlib_only" }
    out = {}
    def walk(obj, p=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{p}{k}{separator}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{p}{i}{separator}")
        else:
            out[p.rstrip(separator)] = obj
    walk(nested)
    return out
