from pathlib import PurePath


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan: list[tuple[str, str]] = []
    for index, old_name in enumerate(filenames):
        ext = PurePath(old_name).suffix
        new_name = pattern.format(n=start + index) + ext
        plan.append((old_name, new_name))
    return plan
