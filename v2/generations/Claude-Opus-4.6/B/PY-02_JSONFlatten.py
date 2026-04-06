def flatten_json(nested: dict, separator: str = ".") -> dict:
    output = {}
    _do_flatten(nested, [], separator, output)
    return output


def _do_flatten(value, path: list, sep: str, result: dict):
    if isinstance(value, dict):
        for k, v in value.items():
            _do_flatten(v, path + [k], sep, result)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _do_flatten(item, path + [str(i)], sep, result)
    else:
        key = sep.join(path)
        result[key] = value
