from typing import List, Tuple
import os

def generate_rename_plan(filenames: List[str], pattern: str, start: int = 1) -> List[Tuple[str, str]]:
    """
    生成文件重命名计划，不实际重命名文件。
    
    Args:
        filenames: 要重命名的文件名列表
        pattern: 命名模板，如 "photo_{n:03d}"
        start: 起始编号（默认为1）
        
    Returns:
        (旧名, 新名) 元组列表
    """
    rename_plan = []
    
    for i, filename in enumerate(filenames):
        base, ext = os.path.splitext(filename)
        new_base = pattern.format(n=start + i)
        new_name = f"{new_base}{ext}"
        rename_plan.append((filename, new_name))
    
    return rename_plan