import os

# [L]Py[F]None[D]StdLib
def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    return [(f, pattern.format(n=i+start) + os.path.splitext(f)[1]) for i, f in enumerate(filenames)]
