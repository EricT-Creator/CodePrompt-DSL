import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    mapping = []
    for seq, old_name in enumerate(filenames, start=start):
        root, ext = os.path.splitext(old_name)
        new_name = pattern.format(n=seq) + ext
        mapping.append((old_name, new_name))
    return mapping
