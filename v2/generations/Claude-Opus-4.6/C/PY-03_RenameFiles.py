import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    counter = start
    for fname in filenames:
        base, ext = os.path.splitext(fname)
        renamed = pattern.format(n=counter) + ext
        plan.append((fname, renamed))
        counter += 1
    return plan
