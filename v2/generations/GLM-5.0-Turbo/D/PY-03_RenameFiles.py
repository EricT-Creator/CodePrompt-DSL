import os
from pathlib import Path


def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    rename_list: list[tuple[str, str]] = []
    for i, fname in enumerate(filenames):
        suffix = Path(fname).suffix
        formatted = pattern.format(n=start + i)
        rename_list.append((fname, formatted + suffix))
    return rename_list
