import re


def extract_info(text: str) -> dict:
    emails = re.findall(r"[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}", text)
    urls = re.findall(r"https?://\S+", text)
    phones = re.findall(r"1[3-9]\d{9}", text)
    return {"emails": emails, "urls": urls, "phones": phones}
