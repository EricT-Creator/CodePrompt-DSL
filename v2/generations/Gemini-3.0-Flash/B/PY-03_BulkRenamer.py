import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    res = []
    for i, name in enumerate(filenames, start):
        base, ext = os.path.splitext(name)
        new_name = pattern.format(n=i) + ext
        res.append((name, new_name))
    return res
