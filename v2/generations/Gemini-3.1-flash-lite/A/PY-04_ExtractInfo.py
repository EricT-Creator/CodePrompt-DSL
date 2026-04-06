import re

def extract_info(text: str) -> dict:
    email_re = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    url_re = r'https?://[a-zA-Z0-9.-]+(?:/[^\s]*)?'
    phone_re = r'1[3-9]\d{9}'
    
    return {
        "emails": re.findall(email_re, text),
        "urls": re.findall(url_re, text),
        "phones": re.findall(phone_re, text)
    }
