def flatten_json(nested: dict, separator: str = ".") -> dict:
    flat_dict = {}

    def flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}{k}{separator}" if prefix else f"{k}{separator}"
                flatten(v, new_key)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                new_key = f"{prefix}{i}{separator}" if prefix else f"{i}{separator}"
                flatten(v, new_key)
        else:
            # Remove trailing separator
            key = prefix[:-len(separator)] if prefix else prefix
            flat_dict[key] = obj

    flatten(nested)
    return flat_dict

if __name__ == "__main__":
    nested = {"a": {"b": 1, "c": [2, {"d": 3}]}}
    print(flatten_json(nested))
    # Expected: {'a.b': 1, 'a.c.0': 2, 'a.c.1.d': 3}
