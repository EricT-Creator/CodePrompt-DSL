from typing import Any


def flatten_json(nested: dict, separator: str = ".") -> dict:
    result: dict[str, Any] = {}
    def _flatten(obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                new_key = f"{prefix}{separator}{idx}" if prefix else str(idx)
                _flatten(item, new_key)
        else:
            result[prefix] = obj
    _flatten(nested, "")
    return result
