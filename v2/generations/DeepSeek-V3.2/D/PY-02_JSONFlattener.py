from typing import Dict, Any

def flatten_json(nested: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """
    将嵌套 JSON 对象拉平为单层字典。
    
    Args:
        nested: 要拉平的嵌套字典
        separator: 键之间的分隔符（默认"."）
        
    Returns:
        拉平后的字典
    """
    result = {}
    
    def flatten(obj, parent_key=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                flatten(value, new_key)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                flatten(value, new_key)
        else:
            result[parent_key] = obj
    
    flatten(nested)
    return result