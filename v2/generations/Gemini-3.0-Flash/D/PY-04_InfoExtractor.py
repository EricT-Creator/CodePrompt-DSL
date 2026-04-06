import re

def extract_info(文: str) -> dict:
    邮式 = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    网式 = r'https?://[^\s,]+'
    机式 = r'1[3-9]\d{9}'
    
    return {
        "emails": re.findall(邮式, 文),
        "urls": re.findall(网式, 文),
        "phones": re.findall(机式, 文)
    }
