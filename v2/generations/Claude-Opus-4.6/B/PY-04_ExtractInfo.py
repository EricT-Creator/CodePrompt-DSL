import re


def extract_info(text: str) -> dict:
    email_pattern = r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}"
    url_pattern = r"https?://[^\s<>\"']+"
    phone_pattern = r"1[3-9]\d{9}"

    found_emails = re.findall(email_pattern, text)
    found_urls = re.findall(url_pattern, text)
    found_phones = re.findall(phone_pattern, text)

    return {
        "emails": found_emails,
        "urls": found_urls,
        "phones": found_phones,
    }
