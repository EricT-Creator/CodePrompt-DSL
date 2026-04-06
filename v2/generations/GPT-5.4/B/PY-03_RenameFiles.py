from pathlib import Path


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    return [
        (name, f"{pattern.format(n=index)}{Path(name).suffix}")
        for index, name in enumerate(filenames, start=start)
    ]
