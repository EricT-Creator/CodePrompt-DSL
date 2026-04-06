def flatten_json(nested: dict, separator: str = ".") -> dict:
    flattened: dict[str, object] = {}

    def descend(node: object, path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                descend(child, path + (str(key),))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                descend(child, path + (str(index),))
        else:
            flattened[separator.join(path)] = node

    descend(nested, ())
    return flattened
