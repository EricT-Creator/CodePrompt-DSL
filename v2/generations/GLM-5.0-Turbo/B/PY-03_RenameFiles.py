import os
from typing import List, Tuple


def generate_rename_plan(
    filenames: List[str], pattern: str, start: int = 1
) -> List[Tuple[str, str]]:
    plan: List[Tuple[str, str]] = []
    counter = start
    for old_name in filenames:
        root, ext = os.path.splitext(old_name)
        new_name = pattern.replace("{n}", str(counter).zfill(3)) + ext
        plan.append((old_name, new_name))
        counter += 1
    return plan
