import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    plan = []
    
    for i, name in enumerate(filenames):
        _, ext = os.path.splitext(name)
        new_name = pattern.format(n=start + i) + ext
        plan.append((name, new_name))
        
    return plan
