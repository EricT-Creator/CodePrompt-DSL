import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"https?://(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[^\s\"'<>]*)?")
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def _matches(pattern: re.Pattern[str], text: str, trim_url: bool = False) -> list[str]:
    values = [match.group(0) for match in pattern.finditer(text)]
    if trim_url:
        return [value.rstrip(".,;!?)") for value in values]
    return values


def extract_info(text: str) -> dict:
    return {
        "emails": _matches(EMAIL, text),
        "urls": _matches(URL, text, trim_url=True),
        "phones": _matches(PHONE, text),
    }
