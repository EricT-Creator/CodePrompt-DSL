from typing import Any


def flatten_json(nested: dict, separator: str = ".") -> dict:
    result: dict[str, Any] = {}
    stack: list[tuple[Any, str]] = [(nested, "")]
    while stack:
        current, prefix = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                new_prefix = f"{prefix}{separator}{key}" if prefix else key
                stack.append((value, new_prefix))
        elif isinstance(current, list):
            for index, item in enumerate(current):
                new_prefix = f"{prefix}{separator}{index}" if prefix else str(index)
                stack.append((item, new_prefix))
        else:
            result[prefix] = current
    return result
