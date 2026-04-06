import re
from typing import Dict, List

def extract_info(text: str) -> Dict[str, List[str]]:
    """
    从文本中提取所有邮箱、URL和中国手机号。
    
    Args:
        text: 要提取信息的输入文本
        
    Returns:
        包含键 "emails", "urls", "phones" 的字典
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .?=&%-]*'
    phone_pattern = r'\b1[3-9]\d{9}\b'
    
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    urls = re.findall(url_pattern, text)
    phones = re.findall(phone_pattern, text)
    
    return {
        "emails": emails,
        "urls": urls,
        "phones": phones
    }