import re


def extract_info(text: str) -> dict:
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    urls = [
        value.rstrip(".,;!?)")
        for value in re.findall(r"https?://[^\s<>'\"]+", text)
    ]
    phones = re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", text)
    return {"emails": emails, "urls": urls, "phones": phones}
