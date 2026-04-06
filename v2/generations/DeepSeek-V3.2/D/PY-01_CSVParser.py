import csv
from io import StringIO
from typing import List, Dict

def parse_csv(text: str) -> List[Dict[str, str]]:
    """
    解析CSV格式字符串（首行为表头）为字典列表。
    正确处理引号内的逗号。
    
    Args:
        text: CSV格式字符串，含表头行
        
    Returns:
        字典列表，键为表头值
    """
    if not text.strip():
        return []
    
    reader = csv.DictReader(StringIO(text))
    result = []
    for row in reader:
        result.append(dict(row))
    return result