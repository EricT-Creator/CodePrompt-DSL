import re

# [L]Py[F]None[D]StdLib
def extract_info(text: str) -> dict:
    return {
        "emails": re.findall(r'[\w.-]+@[\w.-]+\.\w+', text),
        "urls": re.findall(r'https?://[^\s]+', text),
        "phones": re.findall(r'1\d{10}', text)
    }
