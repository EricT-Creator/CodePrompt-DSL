import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_PHONE_RE = re.compile(r"1[3-9]\d{9}")


def extract_info(text: str) -> dict:
    return {
        "emails": _EMAIL_RE.findall(text),
        "urls": _URL_RE.findall(text),
        "phones": _PHONE_RE.findall(text),
    }
