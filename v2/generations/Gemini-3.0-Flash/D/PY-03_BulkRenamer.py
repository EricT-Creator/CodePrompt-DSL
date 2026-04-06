import os

def generate_rename_plan(名列: list[str], 模板: str, 始: int = 1) -> list[tuple[str, str]]:
    果 = []
    for 序, 旧名 in enumerate(名列, 始):
        底, 缀 = os.path.splitext(旧名)
        新名 = 模板.format(n=序) + 缀
        果.append((旧名, 新名))
    return 果
