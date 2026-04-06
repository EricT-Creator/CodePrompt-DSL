import os


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    results = []
    for index, original in enumerate(filenames):
        number = start + index
        _, extension = os.path.splitext(original)
        new_name = pattern.format(n=number) + extension
        results.append((original, new_name))
    return results
