def flatten_json(nested, sep="."):
    res = {}
    def f(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items(): f(v, f"{p}{k}{sep}")
        elif isinstance(o, list):
            for i, v in enumerate(o): f(v, f"{p}{i}{sep}")
        else:
            res[p[:-len(sep)]] = o
    f(nested)
    return res
