from typing import List, Tuple
import os

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    """
    Generate a file rename plan without actually renaming files.
    
    Args:
        filenames: List of file names to rename
        pattern: Naming pattern like "photo_{n:03d}"
        start: Starting number (default 1)
        
    Returns:
        List of (old_name, new_name) tuples
    """
    rename_plan = []
    
    for i, filename in enumerate(filenames):
        # Preserve original extension
        base, ext = os.path.splitext(filename)
        
        # Generate new name using pattern
        new_base = pattern.format(n=start + i)
        new_name = f"{new_base}{ext}"
        
        rename_plan.append((filename, new_name))
    
    return rename_plan