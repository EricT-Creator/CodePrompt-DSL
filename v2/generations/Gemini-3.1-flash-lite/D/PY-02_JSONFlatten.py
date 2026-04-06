# [语]Py[架]None[式]FuncLib[依]StdLib[数据]Mock[出]纯码
def 拉平(嵌套: dict, 分隔: str = ".") -> dict:
    结果 = {}
    def 递归(obj, 前缀=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                递归(v, f"{前缀}{k}{分隔}" if 前缀 else f"{k}{分隔}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                递归(v, f"{前缀}{i}{分隔}")
        else:
            结果[前缀.rstrip(分隔)] = obj
    递归(嵌套)
    return 结果
