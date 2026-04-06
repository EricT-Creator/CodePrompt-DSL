import os

# [语]Py[架]None[式]FuncLib[依]StdLib[数据]Mock[出]纯码
def 生成重命名计划(文件名表: list[str], 模板: str, 起始: int = 1) -> list[tuple[str, str]]:
    计划 = []
    for i, 旧名 in enumerate(文件名表):
        _, 扩展 = os.path.splitext(旧名)
        新名 = 模板.format(n=起始 + i) + 扩展
        计划.append((旧名, 新名))
    return 计划
