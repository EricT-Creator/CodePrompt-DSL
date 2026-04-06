def flatten_json(nested: dict, separator: str = ".") -> dict:
    out = {}
    def step(curr, path=""):
        if isinstance(curr, dict):
            for k, v in curr.items():
                step(v, f"{path}{k}{separator}")
        elif isinstance(curr, list):
            for i, v in enumerate(curr):
                step(v, f"{path}{i}{separator}")
        else:
            out[path.rstrip(separator)] = curr
    step(nested)
    return out
