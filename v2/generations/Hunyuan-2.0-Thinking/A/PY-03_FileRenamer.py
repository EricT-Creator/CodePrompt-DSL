import os
from typing import List, Tuple

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    """Generate rename plan for files"""
    rename_plan = []
    
    for i, old_name in enumerate(filenames):
        # Get file extension
        _, ext = os.path.splitext(old_name)
        
        # Generate new name with pattern
        new_name = pattern.format(n=start + i) + ext
        rename_plan.append((old_name, new_name))
    
    return rename_plan

# Example usage:
if __name__ == "__main__":
    files = ["photo1.jpg", "photo2.png", "document.pdf"]
    plan = generate_rename_plan(files, "vacation_{n:03d}", 1)
    for old, new in plan:
        print(f"{old} -> {new}")