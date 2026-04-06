import re

def extract_info(text: str) -> dict:
    # Constraint: { "dependencies": "stdlib_only" }
    return {
        "emails": re.findall(r'[\w.-]+@[\w.-]+\.\w+', text),
        "urls": re.findall(r'https?://[^\s]+', text),
        "phones": re.findall(r'1\d{10}', text)
    }
