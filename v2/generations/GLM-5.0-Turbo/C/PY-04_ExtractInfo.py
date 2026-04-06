import re


def extract_info(text: str) -> dict:
    return {
        "emails": re.findall(r"[\w.%+-]+@[\w.-]+\.\w{2,}", text),
        "urls": re.findall(r"https?://\S+", text),
        "phones": re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", text),
    }
