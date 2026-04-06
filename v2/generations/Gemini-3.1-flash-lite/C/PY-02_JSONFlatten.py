# [L]Py[F]None[D]StdLib
def flatten_json(nested: dict, sep: str = ".") -> dict:
    def walk(obj, p=""):
        if isinstance(obj, dict):
            return {f"{p}{k}{sep}{subk}" if p else f"{k}{sep}{subk}": subv for k, v in obj.items() for subk, subv in walk(v, "").items()}
        elif isinstance(obj, list):
            return {f"{p}{i}{sep}{subk}" if p else f"{i}{sep}{subk}": subv for i, v in enumerate(obj) for subk, subv in walk(v, "").items()}
        else: return {p.rstrip(sep): obj}
    return walk(nested)
