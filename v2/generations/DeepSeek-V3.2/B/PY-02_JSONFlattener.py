from typing import Dict, Any

def flatten_json(nested: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """
    Flatten a nested JSON object into a flat dictionary.
    
    Args:
        nested: The nested dictionary to flatten
        separator: The separator to use between keys (default ".")
        
    Returns:
        Flattened dictionary
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