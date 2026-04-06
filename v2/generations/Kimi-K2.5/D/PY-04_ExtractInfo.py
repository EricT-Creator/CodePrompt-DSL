import re

def extract_info(text: str) -> dict:
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
    phone_pattern = r'1[3-9]\d{9}'
    
    emails = re.findall(email_pattern, text)
    urls = re.findall(url_pattern, text)
    phones = re.findall(phone_pattern, text)
    
    return {
        "emails": emails,
        "urls": urls,
        "phones": phones
    }
