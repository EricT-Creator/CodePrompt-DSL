import re

def extract_info(text: str) -> dict:
    # Email regex
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # URL regex (Basic version)
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    
    # China Mainland Mobile Phone regex
    # Starts with 1, followed by 3-9, then 9 digits
    phone_pattern = r'1[3-9]\d{9}'
    
    return {
        "emails": re.findall(email_pattern, text),
        "urls": re.findall(url_pattern, text),
        "phones": re.findall(phone_pattern, text)
    }

if __name__ == "__main__":
    sample = "Contact us at support@example.com or visit http://example.com. Call 13812345678 for details."
    print(extract_info(sample))
