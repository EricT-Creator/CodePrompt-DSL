import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    # Constraint: { "dependencies": "stdlib_only" }
    res = []
    for i, old in enumerate(filenames):
        _, ext = os.path.splitext(old)
        new = pattern.format(n=start + i) + ext
        res.append((old, new))
    return res
