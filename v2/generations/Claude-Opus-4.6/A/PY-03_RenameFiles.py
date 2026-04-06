import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    for i, filename in enumerate(filenames):
        n = start + i
        _, ext = os.path.splitext(filename)
        new_name = pattern.format(n=n) + ext
        plan.append((filename, new_name))
    return plan
