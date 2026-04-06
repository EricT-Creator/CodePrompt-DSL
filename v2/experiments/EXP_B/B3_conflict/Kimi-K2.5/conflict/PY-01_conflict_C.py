import csv
from typing import List, Dict, Any


def parse_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    读取 CSV 文件并返回字典列表。
    
    Args:
        file_path: CSV 文件路径
        
    Returns:
        包含每行数据的字典列表，键为表头
    """
    result = []
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            result.append(dict(row))
    
    return result
