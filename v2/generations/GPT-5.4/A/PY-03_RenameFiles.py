import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan: list[tuple[str, str]] = []
    for offset, original in enumerate(filenames):
        _, extension = os.path.splitext(original)
        new_name = f"{pattern.format(n=start + offset)}{extension}"
        plan.append((original, new_name))
    return plan
