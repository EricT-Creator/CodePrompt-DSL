import os

def generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]:
    result = []
    counter = start
    
    for old_name in filenames:
        name, ext = os.path.splitext(old_name)
        new_name = pattern.format(n=counter) + ext
        result.append((old_name, new_name))
        counter += 1
    
    return result
