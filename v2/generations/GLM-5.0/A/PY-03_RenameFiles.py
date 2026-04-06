from typing import List, Tuple
import os

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    result = []
    for i, old_name in enumerate(filenames):
        _, ext = os.path.splitext(old_name)
        new_name = pattern.format(n=start + i) + ext
        result.append((old_name, new_name))
    return result