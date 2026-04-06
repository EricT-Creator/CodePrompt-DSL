from typing import Any, Dict


def flatten_json(nested: Dict, separator: str = ".") -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    def walk(node: Any, parent_key: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                full_key = f"{parent_key}{separator}{k}" if parent_key else k
                walk(v, full_key)
        elif isinstance(node, list):
            for i, elem in enumerate(node):
                full_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                walk(elem, full_key)
        else:
            output[parent_key] = node
    walk(nested)
    return output
