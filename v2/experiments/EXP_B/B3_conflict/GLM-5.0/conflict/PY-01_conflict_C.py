import csv
from typing import List, Dict

def parse_csv(file_path: str) -> List[Dict[str, str]]:
    """
    读取CSV文件并返回字典列表
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        List[Dict[str, str]]: 字典列表，每个字典代表一行数据，键为列名
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def parse_csv_with_delimiter(file_path: str, delimiter: str = ',') -> List[Dict[str, str]]:
    """
    读取CSV文件（可自定义分隔符）并返回字典列表
    
    Args:
        file_path: CSV文件路径
        delimiter: 字段分隔符，默认为逗号
        
    Returns:
        List[Dict[str, str]]: 字典列表，每个字典代表一行数据，键为列名
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [row for row in reader]
