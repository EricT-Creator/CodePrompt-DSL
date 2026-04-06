import os
from typing import List, Tuple

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    plan = []
    
    for i, filename in enumerate(filenames):
        _, ext = os.path.splitext(filename)
        new_name_base = pattern.format(n=start + i)
        new_filename = f"{new_name_base}{ext}"
        plan.append((filename, new_filename))
        
    return plan
