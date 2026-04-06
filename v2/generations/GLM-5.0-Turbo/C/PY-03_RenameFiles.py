import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    out = []
    for i, f in enumerate(filenames):
        _, ext = os.path.splitext(f)
        name = pattern.format(n=start + i) + ext
        out.append((f, name))
    return out
