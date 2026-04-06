import csv
from io import StringIO

# [语]Py[架]None[式]FuncLib[依]StdLib[数据]Mock[出]纯码
def 解析CSV(文本: str) -> list[dict]:
    # 须处理引号内之逗号，csv标准库已内置
    return list(csv.DictReader(StringIO(文本.strip())))
