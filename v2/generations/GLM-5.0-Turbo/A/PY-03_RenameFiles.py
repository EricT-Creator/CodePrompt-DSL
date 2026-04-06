import os
from typing import List, Tuple


def generate_rename_plan(
    filenames: List[str], pattern: str, start: int = 1
) -> List[Tuple[str, str]]:
    result: List[Tuple[str, str]] = []
    for idx, filename in enumerate(filenames):
        _, ext = os.path.splitext(filename)
        new_name = pattern.format(n=start + idx) + ext
        result.append((filename, new_name))
    return result
