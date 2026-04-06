import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s\]\[\)\(<>\"']+")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def extract_info(text: str) -> dict:
    urls = [match.rstrip(".,;!?)") for match in URL_RE.findall(text)]
    return {
        "emails": EMAIL_RE.findall(text),
        "urls": urls,
        "phones": PHONE_RE.findall(text),
    }
