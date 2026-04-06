# CodePrompt-DSL v2 Prompt 模板定义

> **版本**：v2.0 | **日期**：2026-03-31  
> **用途**：定义四种 prompt 变体的模板和填充规则

---

## 一、四种变体模板

### A 组（NL 基线）——纯自然语言

```
Write a {language} {task_type} using {framework}. It should be a {form_description}. Use {style_description} for styling but no other external libraries. The layout should be {layout_description}. {data_instruction}. Only output code, no explanations.

{task_description_en}
```

### B 组（JSON）——自然语言 + JSON 约束

```
Generate code according to this specification:

{
  "language": "{language}",
  "framework": "{framework}",
  "form": "{form}",
  "style": "{style}",
  "dependencies": "{dep_rule}",
  "layout": "{layout}",
  "data": "{data}",
  "output": "code_only"
}

{task_description_en}
```

### C 组（Compact）——英文紧凑 Header + 英文需求

```
===CODE_SPEC===
[L]{lang}[S]{stack}[F]{form}[Y]{style}[D]{dep}[M]{layout}[DT]{data}[O]CODE
===REQ===
{task_description_en}
```

### D 组（Classical）——古文 Header + 古文需求

```
===码制===
[语]{lang}[架]{stack}[式]{form}[样]{style}[依]{dep}[排]{layout}[数]{data}[出]纯码
===需===
{task_description_zh_classical}
```

---

## 二、以 FE-01（登录表单）为例的完整 Prompt

### A 组 Prompt

```
Write a TypeScript React component. It should be a single file component with export default. Use Tailwind CSS for styling but no other external libraries. The layout should be mobile-first. Use mock data. Only output code, no explanations.

Build a login form with an email input field, a password input field, and a login button. Add basic input validation: check that the email has a valid format and the password is not empty. When validation fails, display error messages below the corresponding input fields.
```

### B 组 Prompt

```
Generate code according to this specification:

{
  "language": "TypeScript",
  "framework": "React",
  "form": "single file component with export default",
  "style": "Tailwind CSS",
  "dependencies": "no external libraries",
  "layout": "mobile-first",
  "data": "mock",
  "output": "code_only"
}

Build a login form with an email input field, a password input field, and a login button. Add basic input validation: check that the email has a valid format and the password is not empty. When validation fails, display error messages below the corresponding input fields.
```

### C 组 Prompt

```
===CODE_SPEC===
[L]TS[S]React[F]SFC[Y]TW[D]NOX[M]MOB[DT]MOCK[O]CODE
===REQ===
Build a login form with an email input field, a password input field, and a login button. Add basic input validation: check that the email has a valid format and the password is not empty. When validation fails, display error messages below the corresponding input fields.
```

### D 组 Prompt

```
===码制===
[语]TS[架]React[式]单件[样]TW[依]无外库[排]移动[数]模拟[出]纯码
===需===
作登入表，含邮密二栏与登入键。须校邮之格式、验密之非空，不合则示误。
```

---

## 三、以 BE-02（待办事项 CRUD）为例的完整 Prompt

### A 组 Prompt

```
Write a Python FastAPI application. It should be a single file module. Do not use any external libraries other than fastapi and uvicorn. Only output code, no explanations.

Build a complete CRUD API for todo items. POST /todos to create a new todo, GET /todos to list all todos, GET /todos/{id} to get a single todo, PUT /todos/{id} to update a todo, DELETE /todos/{id} to delete a todo. Store data in an in-memory list.
```

### B 组 Prompt

```
Generate code according to this specification:

{
  "language": "Python",
  "framework": "FastAPI",
  "form": "single file module",
  "dependencies": "no external libraries other than fastapi and uvicorn",
  "output": "code_only"
}

Build a complete CRUD API for todo items. POST /todos to create a new todo, GET /todos to list all todos, GET /todos/{id} to get a single todo, PUT /todos/{id} to update a todo, DELETE /todos/{id} to delete a todo. Store data in an in-memory list.
```

### C 组 Prompt

```
===CODE_SPEC===
[L]PY[S]FastAPI[F]MOD[D]NOX[O]CODE
===REQ===
Build a complete CRUD API for todo items. POST /todos to create a new todo, GET /todos to list all todos, GET /todos/{id} to get a single todo, PUT /todos/{id} to update a todo, DELETE /todos/{id} to delete a todo. Store data in an in-memory list.
```

### D 组 Prompt

```
===码制===
[语]PY[架]FastAPI[式]单模块[依]无外库[出]纯码
===需===
作待办之完整增删改查接口。POST /todos 创建，GET /todos 取全部，GET /todos/{id} 取单条，PUT /todos/{id} 更新，DELETE /todos/{id} 删除。数据存于内存列表即可。
```

---

## 四、以 PY-01（CSV 解析器）为例的完整 Prompt

### A 组 Prompt

```
Write a Python function. It should be a standalone function library in a single file. Use only the Python standard library. Only output code, no explanations.

Write a function called parse_csv that takes a CSV-format string as input (where the first row is the header) and returns a list of dictionaries. Handle commas inside quoted fields correctly (e.g., "Smith, John" should not be split).
```

### B 组 Prompt

```
Generate code according to this specification:

{
  "language": "Python",
  "form": "function library in a single file",
  "dependencies": "standard library only",
  "output": "code_only"
}

Write a function called parse_csv that takes a CSV-format string as input (where the first row is the header) and returns a list of dictionaries. Handle commas inside quoted fields correctly (e.g., "Smith, John" should not be split).
```

### C 组 Prompt

```
===CODE_SPEC===
[L]PY[F]LIB[D]STDLIB[O]CODE
===REQ===
Write a function called parse_csv that takes a CSV-format string as input (where the first row is the header) and returns a list of dictionaries. Handle commas inside quoted fields correctly (e.g., "Smith, John" should not be split).
```

### D 组 Prompt

```
===码制===
[语]PY[式]函数库[依]仅标准库[出]纯码
===需===
写一函数 parse_csv，将 CSV 文本（首行为表头）解析为字典列表。须正确处理引号内之逗号。
```

---

## 五、Header 字段缩写对照表

### C 组（英文 Compact）

| 缩写 | 含义 | 可选值 |
|------|------|--------|
| [L] | Language | TS / PY |
| [S] | Stack/Framework | React / FastAPI / (省略=无框架) |
| [F] | Form | SFC / MOD / LIB / CLI |
| [Y] | Style | TW / CSS / (省略=不适用) |
| [D] | Dependencies | NOX / STDLIB / (省略=无限制) |
| [M] | Layout | MOB / RSP / DSK / (省略=不适用) |
| [DT] | Data | MOCK / (省略=不适用) |
| [O] | Output | CODE |

### D 组（古文 Compact）

| 缩写 | 含义 | 可选值 |
|------|------|--------|
| [语] | 语言 | TS / PY |
| [架] | 框架 | React / FastAPI / (省略=无框架) |
| [式] | 形式 | 单件 / 单模块 / 函数库 / 命令行 |
| [样] | 样式 | TW / CSS / (省略=不适用) |
| [依] | 依赖 | 无外库 / 仅标准库 / (省略=无限制) |
| [排] | 布局 | 移动 / 适应 / 桌面 / (省略=不适用) |
| [数] | 数据 | 模拟 / (省略=不适用) |
| [出] | 输出 | 纯码 |

---

## 六、重要说明

### 为什么 C 组和 D 组的需求描述不同？

- **C 组**的需求描述用**英文**，和 A/B 组相同
- **D 组**的需求描述用**古文**

这是有意为之。v1 发现"闭集约束"压缩后基本无损，真正导致差异的是"开放需求"部分。D 组同时改了 Header 编码和需求语言，这是一个已知的 confound，将在论文 Discussion 中讨论。

### Token 计数方式

每组 prompt 的 input token 数量在实验开始前用统一的 tokenizer（推荐 tiktoken cl100k_base 或 o200k_base）计数并记录。

---

*模板定义完成时间：2026-03-31*
