import re
from typing import Dict, List


def extract_info(text: str) -> Dict[str, List[str]]:
    email_list = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    url_list = re.findall(r"https?://[^\s,;，；）)》\"]+", text)
    phone_list = re.findall(r"1[3-9]\d{9}", text)
    return {
        "emails": email_list,
        "urls": url_list,
        "phones": phone_list,
    }
