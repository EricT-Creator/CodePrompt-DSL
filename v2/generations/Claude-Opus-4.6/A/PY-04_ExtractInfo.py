import re


def extract_info(text: str) -> dict:
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    phones = re.findall(r"1[3-9]\d{9}", text)
    return {"emails": emails, "urls": urls, "phones": phones}
