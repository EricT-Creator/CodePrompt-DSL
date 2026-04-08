# EXP-D: Non-CSS Counter-Intuitive Constraint Extension — 完整执行手册

> **Purpose**: 补充实验，解决 EXP-C 中所有 default-bias failures 均来自 CSS 的结构性弱点  
> **Scale**: 4 tasks × 3 encodings × 3 independent runs = **36 pipelines** (Opus only, full S1→S2→S3)  
> **Date**: 2026-04-08  
> **Status**: S1 完成（12份），S2 完成（36份），S3 完成（36份），评分脚本待执行

---

## 1. 实验背景

### 为什么需要这个实验

EXP-C 的 47 个确认失败中，36 个是 CSS 相关的 default-bias（模型默认用 inline styles/Tailwind 而非指定的 CSS Modules）。这导致审稿人可以说：

> "你真正证明的是 CSS-related styling constraints are special，而不是 engineering constraints broadly behave this way。"

EXP-D 设计了 4 个**非 CSS 领域**的反直觉约束任务，如果结果仍然显示：
1. 反直觉约束失败率更高
2. 失败与编码形式无关
3. 失败机制是 model default bias（不是约束理解失败）

那么 default bias 的泛化性就显著增强。

### 与 EXP-C 的关系

| 维度 | EXP-C | EXP-D |
|------|-------|-------|
| 目的 | 主实验：编码效应 + 传播效应 | 补充实验：非 CSS default bias |
| 任务数 | 12（4 FE + 4 BE + 4 PY） | 4（2 BE + 2 PY，无 FE） |
| 编码条件 | H / NLc / NLf | H / NLc / NLf（同 EXP-C） |
| 重复采样 | 7 combo（3 模型交叉） | 3 independent runs（Opus only） |
| 模型 | Opus + Kimi + DeepSeek | Opus only |
| 管线总数 | 247 | 36 |
| 反直觉约束类型 | CSS Modules (FE), 禁库 (BE/PY) | 禁 logging/Pydantic, 禁 async, 禁 pathlib, 禁 f-string, 禁 urllib, 禁 configparser, 禁 dict |

---

## 2. 四个任务定义

### MC-BE-05: Logging REST API

**需求**: FastAPI CRUD for items (POST/GET/PUT/DELETE /items, GET /items/{id}). Request logging for every call (method, path, timestamp, status_code, response_time_ms) stored in memory list. GET /logs returns logs. GET /logs?level=error filters.

**6 条约束**:

| # | 约束 | 反直觉 | 评分规则 |
|---|------|--------|---------|
| C1 | Python + FastAPI | ❌ | has `from fastapi` or `import fastapi` |
| C2 | **禁 logging 模块，用 print() + 自定义 dict** | ✅ | FAIL if `import logging` or `from logging`; PASS if uses `print(` |
| C3 | **禁 Pydantic BaseModel，raw dict + 手动验证** | ✅ | FAIL if `from pydantic import BaseModel` or `class.*BaseModel`; PASS if manual validation |
| C4 | stdlib + fastapi + uvicorn only | ❌ | only stdlib + fastapi/uvicorn/pydantic imports |
| C5 | 单文件 | ❌ | default PASS |
| C6 | 纯代码输出 | ❌ | no markdown wrapping |

**预期冲突强度**: 高（logging 和 Pydantic 是 FastAPI 的"标准搭配"）

---

### MC-BE-06: Sync File Metadata API

**需求**: FastAPI app, POST /metadata accepts {"paths": [...]} returns file metadata (size_bytes, extension, modified_time, is_directory). Handle non-existent paths gracefully. GET /recent returns 10 most recently queried paths.

**6 条约束**:

| # | 约束 | 反直觉 | 评分规则 |
|---|------|--------|---------|
| C1 | Python + FastAPI | ❌ | has `from fastapi` or `import fastapi` |
| C2 | **禁 async def，全部用同步 def** | ✅ | FAIL if `async def` in route handlers; PASS if all handlers use `def` |
| C3 | **禁 pathlib，只用 os.path** | ✅ | FAIL if `from pathlib` or `import pathlib` or `Path(`; PASS if uses `os.path.` |
| C4 | stdlib + fastapi + uvicorn only | ❌ | only stdlib + fastapi/uvicorn imports |
| C5 | 单文件 | ❌ | default PASS |
| C6 | 纯代码输出 | ❌ | no markdown wrapping |

**预期冲突强度**: 高（FastAPI 教程几乎全用 async def + pathlib）

---

### MC-PY-05: Config File Parser

**需求**: Python class `ConfigParser` that parses INI-style config: key=value pairs, # comments, [section] headers, backslash multi-line continuation. Methods: get(section, key), set(section, key, value), has(section, key), sections(), to_dict(). Raise ConfigError for malformed input.

**6 条约束**:

| # | 约束 | 反直觉 | 评分规则 |
|---|------|--------|---------|
| C1 | Python stdlib only | ❌ | only stdlib imports |
| C2 | **禁 configparser/json/yaml，纯字符串 + re** | ✅ | FAIL if `import configparser` or `import json` or `import yaml`; PASS if uses `re.` or string ops |
| C3 | **禁 dict 存配置，用 NamedTuple/dataclass** | ✅ | FAIL if internal config stored as plain dict; PASS if uses NamedTuple or dataclass with __slots__ |
| C4 | 完整类型标注 | ❌ | ≥50% public methods have return type hints |
| C5 | ConfigError 自定义异常 | ❌ | has `class ConfigError` and `raise ConfigError` |
| C6 | 单文件 class | ❌ | has `class` definition |

**预期冲突强度**: 高（configparser 是 stdlib 标准，dict 是配置存储的默认选择）

---

### MC-PY-06: HTTP Request Builder

**需求**: Python class `HTTPClient` for HTTP/1.1 requests. Methods: get/post/put/delete with headers, params, json_body, timeout. Response dataclass with status_code, headers, body, elapsed_ms. Handle 301/302 redirects (up to 5). Handle timeout.

**6 条约束**:

| # | 约束 | 反直觉 | 评分规则 |
|---|------|--------|---------|
| C1 | Python stdlib only | ❌ | only stdlib imports |
| C2 | **禁 urllib/http.client，用 socket 手写 HTTP** | ✅ | FAIL if `import urllib` or `from urllib` or `import http.client` or `from http`; PASS if `import socket` |
| C3 | **禁 f-string，只用 .format() 或 %** | ✅ | FAIL if `f"` or `f'` appears; PASS if uses `.format(` or `%` |
| C4 | 完整类型标注 | ❌ | ≥50% public methods have return type hints |
| C5 | Response 必须用 dataclass | ❌ | has `@dataclass` and `class Response` |
| C6 | 单文件 class | ❌ | has `class` definition |

**预期冲突强度**: 极高（socket 层 HTTP + 禁 f-string 违反所有现代 Python 实践）

---

## 3. 编码条件（3 种，与 EXP-C 完全一致）

### Header (H)

```
MC-BE-05: [L]Python [F]FastAPI [D]STDLIB+FASTAPI [!LOG]NO_LOGGING_MODULE [!PYDANTIC]NO_BASEMODEL [FILE]SINGLE [OUT]CODE_ONLY
MC-BE-06: [L]Python [F]FastAPI [D]STDLIB+FASTAPI [!ASYNC]SYNC_DEF_ONLY [!PATH]OS_PATH_ONLY [FILE]SINGLE [OUT]CODE_ONLY
MC-PY-05: [L]Python [D]STDLIB_ONLY [!CFG]NO_CONFIGPARSER_JSON_YAML [!DICT]NAMEDTUPLE_OR_DATACLASS_STORAGE [TYPE]FULL_ANNOTATIONS [ERR]ConfigError [OUT]SINGLE_CLASS
MC-PY-06: [L]Python [D]STDLIB_ONLY [!URL]SOCKET_RAW_HTTP [!FSTR]NO_FSTRING [TYPE]FULL_ANNOTATIONS [RES]RESPONSE_DATACLASS [OUT]SINGLE_CLASS
```

### NL-compact (NLc)

简洁自然语言，一段式。示例（MC-BE-05）:
> Python + FastAPI. stdlib + fastapi + uvicorn only. DO NOT use Python logging module — use print() with custom dict format for all logging. DO NOT use Pydantic BaseModel — use raw dict and manual validation. Single file. Code only.

### NL-full (NLf)

详细自然语言，编号列表。示例（MC-BE-05）:
> 1. Use Python with FastAPI framework.
> 2. Only use Python standard library, fastapi, and uvicorn as dependencies.
> 3. Do NOT import or use the Python `logging` module at all. Instead, implement all logging using print() with a custom dict format.
> 4. Do NOT use Pydantic BaseModel for request/response models. Use raw Python dicts and manual validation.
> 5. All code in a single .py file.
> 6. Output code only, no explanation text.

---

## 4. 三阶段执行流程

### Phase 1: S1 Architect (✅ 已完成)

12 份设计文档已生成，路径：
```
v2/experiments/EXP_D/generations/{task}/{enc}_opus_S1/S1_architect.md
```
其中 `{task}` ∈ {MC-BE-05, MC-BE-06, MC-PY-05, MC-PY-06}，`{enc}` ∈ {H, NLc, NLf}

**注意**: 同一任务的 3 个编码条件共享相同的设计文档内容（因为设计是语义等价的）。这与 EXP-C 一致——S1 产出在语义上应该相同，只是约束呈现方式不同。

### Phase 2: S2 Implementer (待执行)

**总量**: 4 tasks × 3 encodings × 3 runs = **36 个代码文件**

**目录结构**:
```
v2/experiments/EXP_D/generations/{task}/{enc}_run{n}/S2_implementer.py
```
例：`MC-BE-05/H_run1/S2_implementer.py`

**每个 S2 prompt 的构造方式**:

1. 读取对应编码的 S2 template：`v2/experiments/EXP_D/prompts/{task}/S2_{enc}_template.md`
2. 读取对应编码的 S1 设计文档：`v2/experiments/EXP_D/generations/{task}/{enc}_opus_S1/S1_architect.md`
3. 将 S2 template 中的 `{S1_OUTPUT}` 替换为 S1 设计文档内容
4. 把完整 prompt 发给 Opus，获得代码输出
5. 保存为 `S2_implementer.py`

**关键**: 每次 run 必须是**独立的对话会话**（新 session），确保输出独立性。

### Phase 3: S3 Auditor (待执行)

**总量**: 36 个审计报告

**目录结构**:
```
v2/experiments/EXP_D/generations/{task}/{enc}_run{n}/S3_auditor.md
```

S3 prompt 构造方式同理，读取 S3 template + S2 代码。

---

## 5. 评分实现

### 评分脚本位置
```
v2/experiments/EXP_D/score_exp_d.py
```

### 评分逻辑（需要实现）

```python
# MC-BE-05
def be05_c1(code): # Python + FastAPI → check import fastapi
def be05_c2(code): # NO logging module → FAIL if `import logging`; PASS if print(
def be05_c3(code): # NO Pydantic BaseModel → FAIL if BaseModel; PASS if raw dict
def be05_c4(code): # stdlib + fastapi only → check_stdlib_plus_fastapi()
def be05_c5(code): # single file → default PASS
def be05_c6(code): # code only → no markdown wrapping

# MC-BE-06
def be06_c1(code): # Python + FastAPI
def be06_c2(code): # NO async def → FAIL if `async def` in handlers; check @app.get/post handlers
def be06_c3(code): # NO pathlib → FAIL if pathlib import or Path(; PASS if os.path
def be06_c4(code): # stdlib + fastapi only
def be06_c5(code): # single file
def be06_c6(code): # code only

# MC-PY-05
def py05_c1(code): # stdlib only
def py05_c2(code): # NO configparser/json/yaml → FAIL if imported
def py05_c3(code): # NO plain dict → FAIL if self._data = {} / self.data: dict; PASS if NamedTuple/dataclass/__slots__
def py05_c4(code): # type annotations
def py05_c5(code): # ConfigError class + raise
def py05_c6(code): # has class

# MC-PY-06
def py06_c1(code): # stdlib only
def py06_c2(code): # NO urllib/http.client → FAIL if imported; PASS if socket
def py06_c3(code): # NO f-string → FAIL if f" or f' pattern found
def py06_c4(code): # type annotations
def py06_c5(code): # @dataclass + Response class
def py06_c6(code): # has class
```

### 输出 CSV 格式（与 EXP-C 的 master.csv 对齐）
```
task, encoding, run, C1, C2, C3, C4, C5, C6, CSR_obj, CSR_normal, CSR_counter, status, notes
```

---

## 6. 分析计划

### 核心问题

1. **非 CSS 反直觉约束的失败率是多少？** 如果 C2/C3 在这 4 个任务上也有 >10% 的失败率，说明 default bias 不限于 CSS。
2. **失败率是否与编码无关？** 比较 H/NLc/NLf 三种编码下的 C2/C3 失败率，如果差异 < 5 pp 且统计不显著，零结果继续成立。
3. **失败机制是否是 default bias？** 检查失败代码：模型是否回退到了被禁止的默认做法（import logging / Pydantic BaseModel / async def / pathlib / urllib / f-string / configparser / dict）。

### 统计检验

- Kruskal-Wallis on CSR across H/NLc/NLf
- Fisher exact test on C2 failure rate across encodings
- Effect size: Cliff's delta
- 与 EXP-C 数据合并后重新检验

### 论文整合

结果将作为 **§4.5 Extension: Non-CSS Counter-Intuitive Constraints (EXP-D)** 整合到 RENE 版论文中。

---

## 7. Prompt 文件位置索引

所有 prompt 已生成完毕（36 个文件）：

```
v2/experiments/EXP_D/prompts/
├── MC-BE-05/
│   ├── S1_header.md          # S1 prompt (H encoding)
│   ├── S1_nl_compact.md      # S1 prompt (NLc encoding)
│   ├── S1_nl_full.md         # S1 prompt (NLf encoding)
│   ├── S2_header_template.md     # S2 template (H) — replace {S1_OUTPUT}
│   ├── S2_nl_compact_template.md # S2 template (NLc)
│   ├── S2_nl_full_template.md    # S2 template (NLf)
│   ├── S3_header_template.md     # S3 template (H) — replace {S2_OUTPUT}
│   ├── S3_nl_compact_template.md # S3 template (NLc)
│   └── S3_nl_full_template.md    # S3 template (NLf)
├── MC-BE-06/  (same structure)
├── MC-PY-05/  (same structure)
└── MC-PY-06/  (same structure)
```

---

## 8. S1 设计文档位置索引

```
v2/experiments/EXP_D/generations/
├── MC-BE-05/
│   ├── H_opus_S1/S1_architect.md
│   ├── NLc_opus_S1/S1_architect.md
│   └── NLf_opus_S1/S1_architect.md
├── MC-BE-06/ (same)
├── MC-PY-05/ (same)
└── MC-PY-06/ (same)
```

---

## 9. 执行清单

- [x] 任务定义（4 个任务 × 6 约束）
- [x] 评分规则（24 条，全部 regex-checkable）
- [x] Prompt 模板（36 个文件）
- [x] S1 设计文档（12 个文件）
- [x] **S2 代码生成（36 个文件）** ✅ 2026-04-08
- [x] **S3 审计报告（36 个文件）** ✅ 2026-04-08
- [x] **评分脚本 `score_exp_d.py`** ✅ 2026-04-08
- [x] 评分 + CSV 输出 ✅ `exp_d_scores.csv`
- [x] 统计分析 ✅ `analysis/EXP_D_REPORT.md`
- [x] **论文整合** ✅ 2026-04-08 (arXiv v5 + RENE v4)

---

## 10. 新会话接手指令

新会话启动后，请执行：

1. 读取本文件 (`v2/experiments/EXP_D/EXP_D_DESIGN.md`)
2. 读取 MEMORY.md 了解项目全局背景
3. 按 Phase 2 规格，逐任务逐编码生成 S2 代码：
   - 读取 S2 template + S1 设计文档
   - 组装完整 prompt
   - 生成代码（每个 run 独立对话）
   - 保存到 `generations/{task}/{enc}_run{n}/S2_implementer.py`
4. 完成 S2 后，执行 Phase 3 (S3 审计)
5. 实现评分脚本 `score_exp_d.py`
6. 运行评分，输出 CSV
7. 分析结果，更新论文
