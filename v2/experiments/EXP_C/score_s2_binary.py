#!/usr/bin/env python3
"""
EXP-C Phase 4 — Layer 2: S2 Binary Constraint Scoring
=====================================================
对每条管线的 S2_implementer 代码做 6 条约束的二值判定 (1=Satisfied / 0=Not Satisfied).
规则来源: EXP_C_SCORING_RULES.md v1.0

输出: constraint_binary_s2.csv
每行 = 一条管线 (task × encoding × combo)
列 = task, encoding, combo, C1, C2, C3, C4, C5, C6, CSR_obj, CSR_normal, CSR_counter, notes

Author: 砚 (automated scoring)
Date: 2026-04-03
"""

import csv
import os
import re
import sys
from pathlib import Path

# ── 配置 ──
GENERATIONS_DIR = Path(__file__).parent / "generations"
OUTPUT_CSV = Path(__file__).parent / "analysis" / "constraint_binary_s2.csv"

TASKS = [
    "MC-FE-01", "MC-FE-02", "MC-FE-03", "MC-FE-04",
    "MC-BE-01", "MC-BE-02", "MC-BE-03", "MC-BE-04",
    "MC-PY-01", "MC-PY-02", "MC-PY-03", "MC-PY-04",
]

ENCODINGS = ["H", "NLc", "NLf"]

COMBOS = ["RRR", "CRR", "SRR", "RCR", "RSR", "RRC", "RRS"]

# S2 已知缺失 (S2 文件不存在, 整管线标 N/A)
S2_KNOWN_MISSING = {
    ("MC-PY-04", "NLf", "RCR"),
    ("MC-PY-03", "H", "RSR"),
    ("MC-PY-04", "H", "RSR"),
    ("MC-PY-02", "NLc", "RSR"),
    ("MC-PY-03", "NLc", "RSR"),
    ("MC-PY-04", "NLc", "RSR"),
}

# ── 工具函数 ──

def read_code(task: str, encoding: str, combo: str) -> str | None:
    """读取 S2 代码文件, 返回内容字符串或 None."""
    dir_name = f"{encoding}_{combo}"
    # FE 任务是 .tsx, BE/PY 是 .py
    if task.startswith("MC-FE"):
        fname = "S2_implementer.tsx"
    else:
        fname = "S2_implementer.py"
    fpath = GENERATIONS_DIR / task / dir_name / fname
    if not fpath.exists():
        return None
    return fpath.read_text(encoding="utf-8", errors="replace")


def has_import(code: str, *packages: str) -> bool:
    """检查代码中是否 import 了指定包."""
    for pkg in packages:
        # 匹配 import xxx, from xxx import, from xxx.yyy import 等
        pattern = rf'(?:^|\n)\s*(?:import\s+{re.escape(pkg)}|from\s+{re.escape(pkg)}(?:\.\w+)*\s+import)'
        if re.search(pattern, code):
            return True
    return False


def count_pattern(code: str, pattern: str) -> int:
    """计算正则匹配次数."""
    return len(re.findall(pattern, code))


def has_pattern(code: str, pattern: str) -> bool:
    """检查是否存在匹配."""
    return bool(re.search(pattern, code))


def has_tailwind_classes(code: str) -> bool:
    """检测 Tailwind 类名模式.
    
    Stricter matching: require Tailwind utility classes to appear as complete tokens 
    (preceded by space, quote, or backtick start), not as substrings of longer class names.
    E.g., 'p-4' matches but 'step-indicator' does not match 'p-'.
    """
    # Extract all className values
    classname_vals = re.findall(r'className=["\'{`]([^"\'`]+)', code)
    if not classname_vals:
        return False
    
    # Tailwind patterns that must appear as whole tokens
    tw_token_patterns = [
        r'(?:^|\s)(?:flex|grid|inline-flex|inline-grid|block|inline-block|hidden)(?:\s|$)',
        r'(?:^|\s)(?:p|m|px|py|mx|my|pt|pb|pl|pr|mt|mb|ml|mr)-\d',
        r'(?:^|\s)(?:bg|text|border|ring)-(?:white|black|gray|red|blue|green|yellow|purple|pink|indigo|slate|zinc)',
        r'(?:^|\s)(?:w|h|min-w|min-h|max-w|max-h)-(?:\d|full|screen|auto)',
        r'(?:^|\s)(?:gap|space)-\d',
        r'(?:^|\s)rounded(?:-\w+)?(?:\s|$)',
        r'(?:^|\s)shadow(?:-\w+)?(?:\s|$)',
    ]
    
    all_classnames = ' '.join(classname_vals)
    for pat in tw_token_patterns:
        if re.search(pat, all_classnames):
            return True
    return False


def has_css_modules_usage(code: str) -> bool:
    """检测 CSS Modules 用法: import from .module.css 或真正的 CSS Modules styles.xxx."""
    # import from .module.css (最可靠的信号)
    if re.search(r"import\s+\w+\s+from\s+['\"].*\.module\.css['\"]", code):
        return True
    # require('./xxx.module.css')
    if re.search(r"require\(['\"].*\.module\.css['\"]\)", code):
        return True
    return False


def has_inline_styles_heavy(code: str) -> bool:
    """检测是否大量使用 inline style (style={{ ... }})."""
    inline_count = count_pattern(code, r'style=\{\{')
    # 如果 > 5 处 inline style, 认为是"主要使用 inline style"
    return inline_count > 5


def is_markdown_wrapped(code: str) -> bool:
    """检查文件是否包含 markdown 围栏或大量解释文本."""
    # 检查 ``` 围栏
    if re.search(r'^```', code, re.MULTILINE):
        return True
    # 检查是否以 # 标题开头 (markdown 文档格式)
    lines = code.strip().split('\n')
    if lines and lines[0].startswith('# '):
        # 可能是 Python 注释, 检查是否是 markdown 标题
        if not lines[0].startswith('#!') and not lines[0].startswith('# -*-'):
            # 如果后续有大量非代码行, 判定为 markdown
            non_code_lines = sum(1 for l in lines[:20] if l.startswith('#') and not l.startswith('#!'))
            if non_code_lines > 5:
                return True
    return False


# ── 标准库模块白名单 ──
PYTHON_STDLIB = {
    "__future__", "abc", "asyncio", "base64", "binascii", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal",
    "enum", "functools", "hashlib", "hmac", "html", "http", "inspect",
    "importlib", "io", "itertools", "json", "logging", "math", "operator", "os",
    "pathlib", "pickle", "queue", "random", "re", "secrets", "shutil",
    "signal", "socket", "sqlite3", "statistics", "string", "struct",
    "sys", "tempfile", "textwrap", "threading", "time", "traceback",
    "typing", "typing_extensions", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml", "zipfile", "zlib", "ast", "types", "dis",
    "configparser", "argparse", "getpass", "glob", "fnmatch",
    "concurrent", "multiprocessing", "subprocess", "array",
}

FASTAPI_ALLOWED = {"fastapi", "uvicorn", "pydantic", "starlette"}


def get_imports(code: str) -> set[str]:
    """提取所有顶级 import 的包名."""
    imports = set()
    for m in re.finditer(r'(?:^|\n)\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)', code):
        pkg = m.group(1) or m.group(2)
        top_level = pkg.split('.')[0]
        imports.add(top_level)
    return imports


def check_only_stdlib(code: str) -> bool:
    """检查是否只用了标准库."""
    imports = get_imports(code)
    for imp in imports:
        if imp not in PYTHON_STDLIB:
            return False
    return True


def check_stdlib_plus_fastapi(code: str) -> bool:
    """检查是否只用了标准库 + fastapi + uvicorn + pydantic."""
    imports = get_imports(code)
    for imp in imports:
        if imp not in PYTHON_STDLIB and imp not in FASTAPI_ALLOWED:
            return False
    return True


# ═══════════════════════════════════════════════════════════
# 各任务的 6 条约束判定函数
# 每个函数返回 (1 or 0, note_string)
# ═══════════════════════════════════════════════════════════

# ── MC-FE-01: Real-time Collaborative Todo Board ──

def fe01_c1(code: str) -> tuple[int, str]:
    """C1: TS + React — .tsx + React import/JSX"""
    has_react = has_pattern(code, r'(?:import\s+React|from\s+["\']react["\']|React\.|<\w+)')
    return (1, "") if has_react else (0, "no React usage detected")

def fe01_c2(code: str) -> tuple[int, str]:
    """C2: CSS Modules, 禁 Tailwind"""
    has_tw = has_tailwind_classes(code) or has_import(code, "tailwindcss")
    has_modules = has_css_modules_usage(code)
    if has_tw:
        return (0, "Tailwind classes detected")
    if has_modules:
        return (1, "")
    # 没有真正的 CSS Modules import -> FAIL
    # 常见情况: const styles = {...} 使用 JS 对象冒充 CSS Modules
    if has_pattern(code, r'styles\.\w+'):
        return (0, "styles.xxx from JS object, not real CSS Modules import")
    return (0, "no CSS Modules usage detected")

def fe01_c3(code: str) -> tuple[int, str]:
    """C3: HTML5 原生拖拽, 禁 dnd 库"""
    has_dnd_lib = has_import(code, "react-dnd", "dnd-kit", "@hello-pangea", "@dnd-kit")
    has_native_drag = has_pattern(code, r'onDrag(?:Start|Over|End|Enter|Leave)|onDrop')
    if has_dnd_lib:
        return (0, "dnd library imported")
    if not has_native_drag:
        return (0, "no HTML5 drag handlers found")
    return (1, "")

def fe01_c4(code: str) -> tuple[int, str]:
    """C4: useReducer only, 禁状态库"""
    has_reducer = has_pattern(code, r'useReducer')
    has_state_lib = has_import(code, "redux", "zustand", "jotai", "recoil", "mobx", "@reduxjs")
    if has_state_lib:
        return (0, "state library imported")
    if not has_reducer:
        return (0, "no useReducer found")
    return (1, "")

def fe01_c5(code: str) -> tuple[int, str]:
    """C5: 单文件 export default"""
    has_export_default = has_pattern(code, r'export\s+default')
    return (1, "") if has_export_default else (0, "no export default")

def fe01_c6(code: str) -> tuple[int, str]:
    """C6: 手写 WS mock, 禁 socket.io"""
    has_socketio = has_import(code, "socket.io", "socket.io-client", "socketio")
    has_mock = has_pattern(code, r'setTimeout|setInterval')
    if has_socketio:
        return (0, "socket.io imported")
    if not has_mock:
        return (0, "no setTimeout/setInterval for WS simulation")
    return (1, "")


# ── MC-FE-02: Virtual Scroll Data Grid ──

def fe02_c1(code: str) -> tuple[int, str]:
    return fe01_c1(code)  # same: TS + React

def fe02_c2(code: str) -> tuple[int, str]:
    """C2: 手写虚拟滚动, 禁 windowing 库"""
    has_lib = has_import(code, "react-window", "react-virtualized", "@tanstack/virtual",
                         "react-virtuoso", "@tanstack/react-virtual")
    has_scroll_calc = has_pattern(code, r'scrollTop|scrollHeight|onScroll|clientHeight')
    if has_lib:
        return (0, "windowing library imported")
    if not has_scroll_calc:
        return (0, "no scroll calculation logic found")
    return (1, "")

def fe02_c3(code: str) -> tuple[int, str]:
    """C3: CSS Modules, 禁 Tailwind/inline"""
    has_tw = has_tailwind_classes(code)
    if has_tw:
        return (0, "Tailwind classes detected")
    has_modules = has_css_modules_usage(code)
    heavy_inline = has_inline_styles_heavy(code)
    if has_modules and not heavy_inline:
        return (1, "")
    if heavy_inline:
        return (0, "heavy inline styles, not CSS Modules")
    # 如果有 styles.xxx 但来自 JS 对象
    if has_pattern(code, r'styles\.\w+'):
        return (0, "styles.xxx from JS object, not CSS Modules import")
    return (0, "no CSS Modules usage detected")

def fe02_c4(code: str) -> tuple[int, str]:
    """C4: 无外部依赖"""
    imports = get_imports(code)
    allowed = {"react", "React", "react-dom", "ReactDOM"}
    for imp in imports:
        if imp in allowed:
            continue
        # CSS Modules 本地导入 (import styles from './xxx.module.css') 不算外部依赖
        # get_imports 会把 styles 提取出来, 但它不是真正的包名
        # 检查是否有 from './xxx' 形式 (本地文件导入)
        local_import_pattern = rf"import\s+{re.escape(imp)}\s+from\s+['\"]\./"
        if re.search(local_import_pattern, code):
            continue
        return (0, f"external import: {imp}")
    return (1, "")

def fe02_c5(code: str) -> tuple[int, str]:
    return fe01_c5(code)  # same: export default

def fe02_c6(code: str) -> tuple[int, str]:
    """C6: 数据内嵌"""
    has_external_data = has_pattern(code, r'import\s+.*\s+from\s+["\']\.\/data|\.\/mock|\.json["\']')
    has_inline_data = has_pattern(code, r'Array\.from|generateData|mockData|MOCK_DATA|Array\(')
    if has_external_data:
        return (0, "imports data from external file")
    if has_inline_data:
        return (1, "")
    # 也检查是否有硬编码数组
    if has_pattern(code, r'const\s+\w*[Dd]ata\w*\s*=\s*\['):
        return (1, "")
    return (1, "inline data assumed")  # 默认通过, 因为大多数情况数据是内嵌的


# ── MC-FE-03: Canvas Drawing Whiteboard ──

def fe03_c1(code: str) -> tuple[int, str]:
    return fe01_c1(code)

def fe03_c2(code: str) -> tuple[int, str]:
    """C2: 手写 Canvas 2D, 禁 canvas 库"""
    has_lib = has_import(code, "fabric", "konva", "p5", "pixi", "paper")
    has_ctx = has_pattern(code, r"getContext\(['\"]2d['\"]\)|CanvasRenderingContext2D")
    if has_lib:
        return (0, "canvas library imported")
    if not has_ctx:
        return (0, "no Canvas 2D context usage found")
    return (1, "")

def fe03_c3(code: str) -> tuple[int, str]:
    """C3: useReducer only, 禁 useState"""
    has_reducer = has_pattern(code, r'useReducer')
    has_usestate = has_pattern(code, r'useState')
    if has_usestate:
        return (0, "useState detected")
    if not has_reducer:
        return (0, "no useReducer found")
    return (1, "")

def fe03_c4(code: str) -> tuple[int, str]:
    return fe02_c4(code)  # same: no external deps

def fe03_c5(code: str) -> tuple[int, str]:
    return fe01_c5(code)

def fe03_c6(code: str) -> tuple[int, str]:
    """C6: 纯代码输出"""
    if is_markdown_wrapped(code):
        return (0, "markdown content detected")
    return (1, "")


# ── MC-FE-04: Multi-Step Form Wizard ──

def fe04_c1(code: str) -> tuple[int, str]:
    return fe01_c1(code)

def fe04_c2(code: str) -> tuple[int, str]:
    """C2: 手写验证, 禁 form/validation 库"""
    has_lib = has_import(code, "react-hook-form", "formik", "zod", "yup",
                         "@hookform", "vest", "joi")
    has_validation = has_pattern(code, r'regex|RegExp|\.test\(|validate|isValid|\.match\(')
    if has_lib:
        return (0, "form/validation library imported")
    if not has_validation:
        return (0, "no hand-written validation logic found")
    return (1, "")

def fe04_c3(code: str) -> tuple[int, str]:
    """C3: plain CSS, 禁 Tailwind"""
    has_tw = has_tailwind_classes(code)
    if has_tw:
        return (0, "Tailwind classes detected")
    # plain CSS 可以是 <style> 标签、CSS 类字符串、或 CSS 文件引用
    has_style_tag = has_pattern(code, r'<style|\.css')
    has_classname = has_pattern(code, r'className=')
    if has_style_tag or has_classname:
        return (1, "")
    return (1, "plain CSS assumed")

def fe04_c4(code: str) -> tuple[int, str]:
    return fe02_c4(code)

def fe04_c5(code: str) -> tuple[int, str]:
    return fe01_c5(code)

def fe04_c6(code: str) -> tuple[int, str]:
    return fe03_c6(code)  # same: 纯代码输出


# ── MC-BE-01: Event-Sourced Task Queue API ──

def be01_c1(code: str) -> tuple[int, str]:
    """C1: Python + FastAPI"""
    has_fastapi = has_import(code, "fastapi")
    return (1, "") if has_fastapi else (0, "no FastAPI import")

def be01_c2(code: str) -> tuple[int, str]:
    """C2: stdlib + fastapi + uvicorn only"""
    return (1, "") if check_stdlib_plus_fastapi(code) else (0, "non-stdlib/fastapi import detected")

def be01_c3(code: str) -> tuple[int, str]:
    """C3: asyncio.Queue, 禁 Celery/RQ"""
    has_celery = has_import(code, "celery", "rq")
    has_queue = has_pattern(code, r'asyncio\.Queue\s*\(')
    if has_celery:
        return (0, "celery/rq imported")
    if not has_queue:
        return (0, "no asyncio.Queue() found")
    return (1, "")

def be01_c4(code: str) -> tuple[int, str]:
    """C4: append-only list event store.
    
    PASS if: uses .append() AND does not overwrite existing event data.
    We exclude initialization patterns like `store[key] = []` or `store[key] = {}` 
    which create new empty containers (not overwrites of existing data).
    """
    has_append = has_pattern(code, r'\.append\(')
    # Destructive operations
    has_del = has_pattern(code, r'del\s+\w*events?\w*\[')
    has_pop = has_pattern(code, r'events?\w*\.pop\(')
    # Dict-key assignment: check if RHS is an empty container (init) or real data (overwrite)
    has_overwrite = False
    for m in re.finditer(r'events?\w*\[\w+\]\s*=\s*(.+)', code):
        rhs = m.group(1).strip()
        if rhs not in ('[]', '{}', 'list()', 'dict()', 'set()'):
            has_overwrite = True
            break
    has_modify = has_del or has_pop or has_overwrite
    if has_modify:
        return (0, "event store has modification operations (del/pop/overwrite)")
    if not has_append:
        return (0, "no .append() for event store found")
    return (1, "")

def be01_c5(code: str) -> tuple[int, str]:
    """C5: 所有端点幂等"""
    has_idempotency = has_pattern(code, r'idempoten|idempotency.key|Idempotency')
    return (1, "") if has_idempotency else (0, "no idempotency mechanism detected")

def be01_c6(code: str) -> tuple[int, str]:
    """C6: 纯代码输出"""
    if is_markdown_wrapped(code):
        return (0, "markdown content detected")
    return (1, "")


# ── MC-BE-02: JWT Auth Middleware ──

def be02_c1(code: str) -> tuple[int, str]:
    return be01_c1(code)

def be02_c2(code: str) -> tuple[int, str]:
    """C2: 手写 JWT, 禁 PyJWT/jose"""
    has_lib = has_import(code, "jwt", "jose", "PyJWT", "python_jose", "authlib")
    has_manual = has_pattern(code, r'hmac|base64') and has_pattern(code, r'sha256|SHA256|sha_256')
    if has_lib:
        return (0, "JWT library imported")
    if not has_manual:
        return (0, "no manual JWT signing (hmac+base64+sha256) found")
    return (1, "")

def be02_c3(code: str) -> tuple[int, str]:
    """C3: stdlib + fastapi + uvicorn"""
    return (1, "") if check_stdlib_plus_fastapi(code) else (0, "non-stdlib/fastapi import detected")

def be02_c4(code: str) -> tuple[int, str]:
    """C4: 单文件"""
    return (1, "")  # 我们只看一个文件, 无法判断是否有多文件; 默认通过

def be02_c5(code: str) -> tuple[int, str]:
    """C5: login/protected/refresh 端点"""
    has_login = has_pattern(code, r'/login|login|authenticate')
    has_protected = has_pattern(code, r'/protected|protected|/me|/profile')
    has_refresh = has_pattern(code, r'/refresh|refresh')
    missing = []
    if not has_login:
        missing.append("login")
    if not has_protected:
        missing.append("protected")
    if not has_refresh:
        missing.append("refresh")
    if missing:
        return (0, f"missing endpoints: {', '.join(missing)}")
    return (1, "")

def be02_c6(code: str) -> tuple[int, str]:
    return be01_c6(code)


# ── MC-BE-03: WebSocket Chat Server ──

def be03_c1(code: str) -> tuple[int, str]:
    return be01_c1(code)

def be03_c2(code: str) -> tuple[int, str]:
    """C2: 禁 asyncio.Queue 广播, 用 set 遍历"""
    # 检查是否用了 asyncio.Queue 做广播
    has_async_queue = has_pattern(code, r'asyncio\.Queue\s*\(')
    # 检查是否有 set 遍历广播
    has_set_iter = has_pattern(code, r'for\s+\w+\s+in\s+\w*connections?\w*|for\s+\w+\s+in\s+\w*clients?\w*')
    if has_async_queue:
        return (0, "asyncio.Queue used (possibly for broadcast)")
    if not has_set_iter:
        return (0, "no set iteration for broadcast found")
    return (1, "")

def be03_c3(code: str) -> tuple[int, str]:
    """C3: fastapi + uvicorn only"""
    return (1, "") if check_stdlib_plus_fastapi(code) else (0, "non-fastapi import detected")

def be03_c4(code: str) -> tuple[int, str]:
    """C4: 单文件"""
    return (1, "")  # 默认通过

def be03_c5(code: str) -> tuple[int, str]:
    """C5: 消息历史 list ≤100 条"""
    has_history = has_pattern(code, r'history|messages|message_log')
    has_limit = has_pattern(code, r'maxlen\s*=\s*100|len\(\w*\)\s*>\s*100|[:]\s*100\]|\[-100:\]|100')
    if not has_history:
        return (0, "no message history found")
    if not has_limit:
        return (0, "no 100-message limit found")
    return (1, "")

def be03_c6(code: str) -> tuple[int, str]:
    return be01_c6(code)


# ── MC-BE-04: Rate Limiter Middleware ──

def be04_c1(code: str) -> tuple[int, str]:
    return be01_c1(code)

def be04_c2(code: str) -> tuple[int, str]:
    """C2: Token Bucket 算法, 禁简单计数器"""
    has_bucket = has_pattern(code, r'[Tt]oken[_\s]?[Bb]ucket|tokens?\s*[=<>+]|refill|capacity|burst')
    has_time_refill = has_pattern(code, r'time\.\w+|elapsed|interval|last_\w*time')
    if has_bucket and has_time_refill:
        return (1, "")
    if has_bucket:
        return (1, "token bucket pattern found")
    return (0, "no token bucket algorithm detected")

def be04_c3(code: str) -> tuple[int, str]:
    """C3: stdlib + fastapi, 禁 Redis"""
    has_redis = has_import(code, "redis", "memcached", "aioredis")
    if has_redis:
        return (0, "Redis/memcached imported")
    return (1, "") if check_stdlib_plus_fastapi(code) else (0, "non-stdlib import detected")

def be04_c4(code: str) -> tuple[int, str]:
    """C4: 单文件"""
    return (1, "")

def be04_c5(code: str) -> tuple[int, str]:
    """C5: 429 + Retry-After + 白名单 (case-insensitive for whitelist)"""
    has_429 = has_pattern(code, r'429|HTTP_429|TOO_MANY')
    has_retry = has_pattern(code, r'[Rr]etry[_-]?[Aa]fter')
    has_whitelist = bool(re.search(
        r'whitelist|white_list|allowlist|allow_list|exempt|bypass|WHITELIST|WHITE_LIST|ALLOWLIST|ALLOW_LIST|IP_WHITELIST|IP_ALLOWLIST',
        code, re.IGNORECASE
    ))
    missing = []
    if not has_429:
        missing.append("429")
    if not has_retry:
        missing.append("Retry-After")
    if not has_whitelist:
        missing.append("whitelist")
    if missing:
        return (0, f"missing: {', '.join(missing)}")
    return (1, "")

def be04_c6(code: str) -> tuple[int, str]:
    return be01_c6(code)


# ── MC-PY-01: Plugin-based Data Pipeline ──

def py01_c1(code: str) -> tuple[int, str]:
    """C1: Python 3.10+, stdlib only"""
    return (1, "") if check_only_stdlib(code) else (0, "non-stdlib import detected")

def py01_c2(code: str) -> tuple[int, str]:
    """C2: exec() 加载, 禁 importlib"""
    has_importlib = has_import(code, "importlib")
    has_exec = has_pattern(code, r'exec\s*\(')
    if has_importlib:
        return (0, "importlib imported")
    if not has_exec:
        return (0, "no exec() call found")
    return (1, "")

def py01_c3(code: str) -> tuple[int, str]:
    """C3: Protocol 接口, 禁 ABC.
    
    FAIL if: actual 'from abc import' or 'import abc' statement exists.
    PASS if: uses Protocol and no real abc import.
    Ignore ABC appearing in comments, docstrings, or header strings.
    """
    # Only check actual import statements, not comments/strings
    has_abc_import = has_import(code, "abc")
    # Also check for 'from abc import ABC/abstractmethod' specifically
    has_abc_usage = bool(re.search(r'(?:^|\n)\s*from\s+abc\s+import', code))
    has_protocol = has_pattern(code, r'Protocol')
    if has_abc_import or has_abc_usage:
        return (0, "ABC/abstractmethod imported")
    if not has_protocol:
        return (0, "no Protocol interface found")
    return (1, "")

def py01_c4(code: str) -> tuple[int, str]:
    """C4: 完整类型标注"""
    # 检查 public 方法是否有类型标注
    # 找所有 def xxx(...) 且不是 _xxx 的方法
    methods = re.findall(r'def\s+([a-zA-Z]\w*)\s*\((.*?)\)', code)
    if not methods:
        return (0, "no public methods found")
    annotated = 0
    total = 0
    for name, params in methods:
        if name.startswith('_') and name != '__init__':
            continue
        total += 1
        # 检查返回值标注: -> xxx:
        method_pattern = rf'def\s+{re.escape(name)}\s*\([^)]*\)\s*->'
        if re.search(method_pattern, code):
            annotated += 1
    if total == 0:
        return (1, "no public methods to check")
    ratio = annotated / total
    return (1, "") if ratio >= 0.5 else (0, f"only {annotated}/{total} methods have return type hints")

def py01_c5(code: str) -> tuple[int, str]:
    """C5: 错误隔离"""
    has_try_except = has_pattern(code, r'try\s*:')
    has_plugin_context = has_pattern(code, r'plugin|transform|execute|run')
    if has_try_except and has_plugin_context:
        return (1, "")
    return (0, "no error isolation for plugins")

def py01_c6(code: str) -> tuple[int, str]:
    """C6: 单文件 class 输出"""
    has_class = has_pattern(code, r'class\s+\w+')
    return (1, "") if has_class else (0, "no class found")


# ── MC-PY-02: DAG Task Scheduler ──

def py02_c1(code: str) -> tuple[int, str]:
    return py01_c1(code)

def py02_c2(code: str) -> tuple[int, str]:
    """C2: 禁 networkx/graphlib"""
    has_lib = has_import(code, "networkx", "graphlib")
    if has_lib:
        return (0, "graph library imported")
    # 检查手写拓扑排序
    has_topo = has_pattern(code, r'topolog|in.?degree|indegree|DFS|dfs|visited|sorted_order|kahn')
    if not has_topo:
        return (0, "no topological sort implementation found")
    return (1, "")

def py02_c3(code: str) -> tuple[int, str]:
    """C3: 输出为 class"""
    has_class = has_pattern(code, r'class\s+\w*(?:DAG|Scheduler|Task)\w*')
    return (1, "") if has_class else (0, "no DAG/Scheduler class found")

def py02_c4(code: str) -> tuple[int, str]:
    return py01_c4(code)  # 完整类型标注

def py02_c5(code: str) -> tuple[int, str]:
    """C5: CycleError 自定义异常"""
    has_cycle_error = has_pattern(code, r'class\s+CycleError')
    has_raise = has_pattern(code, r'raise\s+CycleError')
    if not has_cycle_error:
        return (0, "no CycleError class defined")
    if not has_raise:
        return (0, "CycleError defined but never raised")
    return (1, "")

def py02_c6(code: str) -> tuple[int, str]:
    """C6: 单文件"""
    return (1, "")  # 单文件默认通过


# ── MC-PY-03: Template Engine ──

def py03_c1(code: str) -> tuple[int, str]:
    return py01_c1(code)

def py03_c2(code: str) -> tuple[int, str]:
    """C2: 正则解析, 禁 jinja2/mako"""
    has_lib = has_import(code, "jinja2", "mako", "jinja", "django")
    has_regex = has_pattern(code, r're\.compile|re\.findall|re\.sub|re\.search|re\.match')
    if has_lib:
        return (0, "template library imported")
    if not has_regex:
        return (0, "no regex parsing found")
    return (1, "")

def py03_c3(code: str) -> tuple[int, str]:
    """C3: 禁 ast 模块.
    
    FAIL if: actual 'import ast' or 'from ast import' exists.
    PASS if: no real ast import (local variable named 'ast' is OK).
    """
    has_ast_import = has_import(code, "ast")
    if has_ast_import:
        return (0, "ast module imported")
    return (1, "")

def py03_c4(code: str) -> tuple[int, str]:
    return py01_c4(code)

def py03_c5(code: str) -> tuple[int, str]:
    """C5: TemplateSyntaxError 自定义异常"""
    has_error = has_pattern(code, r'class\s+TemplateSyntaxError')
    has_raise = has_pattern(code, r'raise\s+TemplateSyntaxError')
    if not has_error:
        return (0, "no TemplateSyntaxError class")
    if not has_raise:
        return (0, "TemplateSyntaxError defined but never raised")
    return (1, "")

def py03_c6(code: str) -> tuple[int, str]:
    """C6: 单文件 class 输出"""
    has_class = has_pattern(code, r'class\s+\w*(?:Template|Engine)\w*')
    return (1, "") if has_class else (0, "no Template/Engine class found")


# ── MC-PY-04: AST Code Checker ──

def py04_c1(code: str) -> tuple[int, str]:
    return py01_c1(code)

def py04_c2(code: str) -> tuple[int, str]:
    """C2: 必须 ast.NodeVisitor, 禁正则做代码检查"""
    has_visitor = has_pattern(code, r'ast\.NodeVisitor|NodeVisitor|ast\.walk')
    has_regex_check = has_pattern(code, r're\.search.*import|re\.findall.*def\s')
    if not has_visitor:
        return (0, "no ast.NodeVisitor/ast.walk usage")
    # 允许 re 用于非代码检查目的 (如 string processing)
    # 这里只标记明显用 regex 做代码分析的情况
    return (1, "")

def py04_c3(code: str) -> tuple[int, str]:
    """C3: dataclass 输出"""
    has_dataclass = has_pattern(code, r'@dataclass|dataclass')
    return (1, "") if has_dataclass else (0, "no @dataclass found")

def py04_c4(code: str) -> tuple[int, str]:
    return py01_c4(code)

def py04_c5(code: str) -> tuple[int, str]:
    """C5: 四种检查全实现"""
    checks = {
        "unused_import": has_pattern(code, r'unused.?import|import.*check|ImportCheck|unused.*import'),
        "unused_var": has_pattern(code, r'unused.?var|variable.*check|VarCheck|unused.*variable|unused.*name'),
        "func_length": has_pattern(code, r'function.?length|long.?func|FunctionLength|too.?long|50'),
        "nesting_depth": has_pattern(code, r'nest.*depth|deep.*nest|NestingDepth|nesting|depth.*check'),
    }
    missing = [k for k, v in checks.items() if not v]
    if missing:
        return (0, f"missing checks: {', '.join(missing)}")
    return (1, "")

def py04_c6(code: str) -> tuple[int, str]:
    """C6: 单文件 class 输出"""
    has_class = has_pattern(code, r'class\s+\w*(?:Code|Check|Lint|Analyz)\w*')
    return (1, "") if has_class else (0, "no CodeChecker-like class found")


# ═══════════════════════════════════════════════════════════
# 判定规则映射表
# ═══════════════════════════════════════════════════════════

RULES = {
    "MC-FE-01": [fe01_c1, fe01_c2, fe01_c3, fe01_c4, fe01_c5, fe01_c6],
    "MC-FE-02": [fe02_c1, fe02_c2, fe02_c3, fe02_c4, fe02_c5, fe02_c6],
    "MC-FE-03": [fe03_c1, fe03_c2, fe03_c3, fe03_c4, fe03_c5, fe03_c6],
    "MC-FE-04": [fe04_c1, fe04_c2, fe04_c3, fe04_c4, fe04_c5, fe04_c6],
    "MC-BE-01": [be01_c1, be01_c2, be01_c3, be01_c4, be01_c5, be01_c6],
    "MC-BE-02": [be02_c1, be02_c2, be02_c3, be02_c4, be02_c5, be02_c6],
    "MC-BE-03": [be03_c1, be03_c2, be03_c3, be03_c4, be03_c5, be03_c6],
    "MC-BE-04": [be04_c1, be04_c2, be04_c3, be04_c4, be04_c5, be04_c6],
    "MC-PY-01": [py01_c1, py01_c2, py01_c3, py01_c4, py01_c5, py01_c6],
    "MC-PY-02": [py02_c1, py02_c2, py02_c3, py02_c4, py02_c5, py02_c6],
    "MC-PY-03": [py03_c1, py03_c2, py03_c3, py03_c4, py03_c5, py03_c6],
    "MC-PY-04": [py04_c1, py04_c2, py04_c3, py04_c4, py04_c5, py04_c6],
}

# 反直觉约束位 (C2 和 C3 在所有 12 个任务中都是反直觉的)
COUNTER_INTUITIVE = {"C2", "C3"}
NORMAL = {"C1", "C4", "C5", "C6"}


# ═══════════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    stats = {"total": 0, "scored": 0, "missing": 0, "skip": 0}

    for task in TASKS:
        for enc in ENCODINGS:
            for combo in COMBOS:
                stats["total"] += 1
                pipeline_id = f"{task}/{enc}_{combo}"

                # 已知 S2 缺失
                if (task, enc, combo) in S2_KNOWN_MISSING:
                    rows.append({
                        "task": task, "encoding": enc, "combo": combo,
                        "C1": "N/A", "C2": "N/A", "C3": "N/A",
                        "C4": "N/A", "C5": "N/A", "C6": "N/A",
                        "CSR_obj": "N/A", "CSR_normal": "N/A",
                        "CSR_counter": "N/A", "status": "S2_MISSING",
                        "notes": "S2 file missing (known)"
                    })
                    stats["skip"] += 1
                    continue

                # 读取代码
                code = read_code(task, enc, combo)
                if code is None:
                    rows.append({
                        "task": task, "encoding": enc, "combo": combo,
                        "C1": "N/A", "C2": "N/A", "C3": "N/A",
                        "C4": "N/A", "C5": "N/A", "C6": "N/A",
                        "CSR_obj": "N/A", "CSR_normal": "N/A",
                        "CSR_counter": "N/A", "status": "FILE_MISSING",
                        "notes": "S2 file not found"
                    })
                    stats["missing"] += 1
                    print(f"  ⚠️  MISSING: {pipeline_id}")
                    continue

                # 执行 6 条规则
                checkers = RULES[task]
                scores = {}
                all_notes = []
                for i, checker in enumerate(checkers):
                    c_name = f"C{i+1}"
                    score, note = checker(code)
                    scores[c_name] = score
                    if note:
                        all_notes.append(f"{c_name}: {note}")

                # 计算 CSR
                vals = [scores[f"C{i}"] for i in range(1, 7)]
                csr_obj = sum(vals) / 6
                csr_normal = sum(scores[c] for c in NORMAL) / 4
                csr_counter = sum(scores[c] for c in COUNTER_INTUITIVE) / 2

                rows.append({
                    "task": task, "encoding": enc, "combo": combo,
                    "C1": scores["C1"], "C2": scores["C2"], "C3": scores["C3"],
                    "C4": scores["C4"], "C5": scores["C5"], "C6": scores["C6"],
                    "CSR_obj": f"{csr_obj:.3f}",
                    "CSR_normal": f"{csr_normal:.3f}",
                    "CSR_counter": f"{csr_counter:.3f}",
                    "status": "SCORED",
                    "notes": "; ".join(all_notes) if all_notes else ""
                })
                stats["scored"] += 1

    # 写 CSV
    fieldnames = [
        "task", "encoding", "combo",
        "C1", "C2", "C3", "C4", "C5", "C6",
        "CSR_obj", "CSR_normal", "CSR_counter",
        "status", "notes"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # 打印统计
    print(f"\n{'='*60}")
    print(f"EXP-C Phase 4 — Layer 2: S2 Binary Constraint Scoring")
    print(f"{'='*60}")
    print(f"Total pipelines:  {stats['total']}")
    print(f"Scored:           {stats['scored']}")
    print(f"S2 missing (skip):{stats['skip']}")
    print(f"File missing:     {stats['missing']}")
    print(f"Output:           {OUTPUT_CSV}")

    # 汇总统计
    scored_rows = [r for r in rows if r["status"] == "SCORED"]
    if scored_rows:
        avg_csr = sum(float(r["CSR_obj"]) for r in scored_rows) / len(scored_rows)
        avg_normal = sum(float(r["CSR_normal"]) for r in scored_rows) / len(scored_rows)
        avg_counter = sum(float(r["CSR_counter"]) for r in scored_rows) / len(scored_rows)
        print(f"\n--- Aggregate Stats ---")
        print(f"Mean CSR-obj:     {avg_csr:.3f}")
        print(f"Mean CSR-normal:  {avg_normal:.3f}")
        print(f"Mean CSR-counter: {avg_counter:.3f}")

        # 按 encoding 分组
        print(f"\n--- By Encoding ---")
        for enc in ENCODINGS:
            enc_rows = [r for r in scored_rows if r["encoding"] == enc]
            if enc_rows:
                avg = sum(float(r["CSR_obj"]) for r in enc_rows) / len(enc_rows)
                print(f"  {enc:5s}: CSR-obj = {avg:.3f}  (n={len(enc_rows)})")

        # 按 combo 分组
        print(f"\n--- By Combo ---")
        for combo in COMBOS:
            c_rows = [r for r in scored_rows if r["combo"] == combo]
            if c_rows:
                avg = sum(float(r["CSR_obj"]) for r in c_rows) / len(c_rows)
                print(f"  {combo:5s}: CSR-obj = {avg:.3f}  (n={len(c_rows)})")

        # 按 domain 分组
        print(f"\n--- By Domain ---")
        for domain, prefix in [("Frontend", "MC-FE"), ("Backend", "MC-BE"), ("Python", "MC-PY")]:
            d_rows = [r for r in scored_rows if r["task"].startswith(prefix)]
            if d_rows:
                avg = sum(float(r["CSR_obj"]) for r in d_rows) / len(d_rows)
                print(f"  {domain:10s}: CSR-obj = {avg:.3f}  (n={len(d_rows)})")

        # C2/C3 (反直觉) vs C1/C4/C5/C6 (常规) 对比
        print(f"\n--- Counter-Intuitive vs Normal ---")
        print(f"  Normal (C1,C4,C5,C6):       {avg_normal:.3f}")
        print(f"  Counter-Intuitive (C2,C3):   {avg_counter:.3f}")
        print(f"  Gap:                         {avg_normal - avg_counter:+.3f}")

    print(f"\n✅ Done. CSV saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
