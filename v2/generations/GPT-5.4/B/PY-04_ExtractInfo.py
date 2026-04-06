import re

email_pattern = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
url_pattern = re.compile(r'https?://[^\s<>"]+')
phone_pattern = re.compile(r"(?<!\d)(?:\+?86[- ]?)?(1[3-9]\d{9})(?!\d)")


def extract_info(text: str) -> dict:
    emails = [match.group(0) for match in email_pattern.finditer(text)]
    urls = [match.group(0).rstrip(".,;!?)") for match in url_pattern.finditer(text)]
    phones = [match.group(1) for match in phone_pattern.finditer(text)]
    return {"emails": emails, "urls": urls, "phones": phones}
