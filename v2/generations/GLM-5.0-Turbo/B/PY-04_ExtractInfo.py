import re


def extract_info(text: str) -> dict:
    EMAIL_RE = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    URL_RE = r"https?://(?:[-\w.]|(?:%[0-9a-fA-F]{2}))+[/\w .-]*/?"
    PHONE_RE = r"(?<!\d)1[3-9]\d{9}(?!\d)"

    return {
        "emails": re.findall(EMAIL_RE, text),
        "urls": re.findall(URL_RE, text),
        "phones": re.findall(PHONE_RE, text),
    }
