import os
from typing import List, Tuple

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    plan = []
    current_index = start
    
    for filename in filenames:
        _, ext = os.path.splitext(filename)
        new_name_base = pattern.format(n=current_index)
        new_name = f"{new_name_base}{ext}"
        plan.append((filename, new_name))
        current_index += 1
        
    return plan
