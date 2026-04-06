import csv
from io import StringIO

def parse_csv(text: str) -> list[dict]:
    """
    将 CSV 文本解析为字典列表（首行作为标题）。
    正确处理引号内的逗号。
    
    Args:
        text: CSV 格式的文本字符串
        
    Returns:
        字典列表，每个字典代表一行，键为列名
        
    Example:
        >>> parse_csv('name,age\\n"Alice, Bob",25\\nCharlie,30')
        [{'name': 'Alice, Bob', 'age': '25'}, {'name': 'Charlie', 'age': '30'}]
    """
    reader = csv.DictReader(StringIO(text))
    return [row for row in reader]
