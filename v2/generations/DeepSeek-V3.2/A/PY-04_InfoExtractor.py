import re
from typing import Dict, List

def extract_info(text: str) -> Dict[str, List[str]]:
    """
    Extract emails, URLs, and Chinese phone numbers from text.
    
    Args:
        text: Input text to extract information from
        
    Returns:
        Dictionary with keys: "emails", "urls", "phones"
    """
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # URL pattern
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .?=&%-]*'
    
    # Chinese phone number pattern (mobile)
    phone_pattern = r'\b1[3-9]\d{9}\b'
    
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    urls = re.findall(url_pattern, text)
    phones = re.findall(phone_pattern, text)
    
    return {
        "emails": emails,
        "urls": urls,
        "phones": phones
    }