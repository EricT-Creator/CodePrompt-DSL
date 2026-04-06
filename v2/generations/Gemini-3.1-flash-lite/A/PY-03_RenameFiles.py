import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    for i, old_name in enumerate(filenames):
        ext = os.path.splitext(old_name)[1]
        new_name = pattern.format(n=start + i) + ext
        plan.append((old_name, new_name))
    return plan
