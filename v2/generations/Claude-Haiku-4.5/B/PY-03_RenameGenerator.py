import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    for i, filename in enumerate(filenames, start=start):
        name, ext = os.path.splitext(filename)
        new_name = pattern.format(n=i) + ext
        plan.append((filename, new_name))
    return plan
