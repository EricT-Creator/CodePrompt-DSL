import re

# [语]Py[架]None[式]FuncLib[依]StdLib[数据]Mock[出]纯码
def 提取信息(文本: str) -> dict:
    return {
        "emails": re.findall(r'[\w.-]+@[\w.-]+\.\w+', 文本),
        "urls": re.findall(r'https?://[^\s]+', 文本),
        "phones": re.findall(r'1\d{10}', 文本)
    }
