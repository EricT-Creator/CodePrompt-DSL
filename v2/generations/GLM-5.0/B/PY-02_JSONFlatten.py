from typing import Dict, Any, Union

def flatten_json(nested: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    result = {}
    
    def flatten(obj: Union[Dict, list], prefix: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                if isinstance(value, dict):
                    flatten(value, new_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        flatten(item, f"{new_key}{separator}{i}")
                else:
                    result[new_key] = value
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}{separator}{i}" if prefix else str(i)
                if isinstance(item, dict):
                    flatten(item, new_key)
                elif isinstance(item, list):
                    flatten(item, new_key)
                else:
                    result[new_key] = item
    
    flatten(nested)
    return result