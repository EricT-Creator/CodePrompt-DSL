# CodePrompt-DSL v2 人工代码审查指南

> **请求人**：Tang, Hanzhang
> **预计耗时**：3-4 小时
> **所需背景**：能看懂 React/TypeScript 和 Python 代码
> **日期**：2026-04-06

---

## 一、背景

我在做一篇关于"LLM 代码生成中紧凑约束编码"的研究论文。核心实验是：用三种不同格式（紧凑 Header / 简洁自然语言 / 完整自然语言）给 LLM 写 prompt，让它生成代码，然后检查生成的代码是否遵循了 6 条工程约束。

**约束满足率（CSR）** 目前由自动化 regex 评分器打分（PASS/FAIL）。论文中承诺做人工抽检以验证自动评分的准确性。

**你需要做的**：对 97 个"自动评分 × 约束"组合进行人工复核，判断自动评分是否正确。

---

## 二、审查任务分两部分

### 任务 A：Regex 评分器验证（97 项，约 3-4 小时）

从 `human_review_sample_v2.csv` 中逐行检查。

每行代表一个 **文件 × 约束** 的评分。你需要：

1. 打开 `file_path` 指向的代码文件
2. 根据下面的"约束评分标准"判断该约束是 PASS 还是 FAIL
3. 在 `human_score` 列填写你的判断（PASS / FAIL）
4. 如果你的判断与 `auto_score` 不同，在 `human_notes` 中简要说明原因

**重点关注**：全部 67 个 FAIL 样本 + 30 个随机 PASS 样本。

### 任务 B：新补数据的评分验证（2 项，约 5 分钟）

原有 6 条 INCOMPLETE_S2 中，实际补完了 2 条（其余 4 条因 DeepSeek 模型不稳定决定保持 INCOMPLETE）：

1. **MC-PY-02 / NLc / RSR**（DeepSeek）→ `v2/experiments/EXP_C/generations/MC-PY-02/NLc_RSR/S2_implementer.py`
2. **MC-PY-04 / NLf / RCR**（Kimi）→ `v2/experiments/EXP_C/generations/MC-PY-04/NLf_RCR/S2_implementer.py`

对这 2 个文件的自动评分结果做人工确认（各 6 条约束 = 12 个判断）。

---

## 三、约束评分标准

每个任务有 6 条约束（C1-C6），分两类：

- **普通约束** (C1, C4, C5, C6)：通常是技术选择、输出格式等
- **反直觉约束** (C2, C3)：与模型常见默认做法相反

### 前端任务 (FE-01 ~ FE-04)

| 约束 | 类型 | 检查什么 | PASS 条件 | FAIL 条件 |
|------|------|---------|-----------|-----------|
| **C1** | 普通 | React + TypeScript | 代码是 .tsx 格式，使用 React 组件 | 使用 Vue/Angular/纯 HTML 等 |
| **C2** | 反直觉 | CSS Modules 样式 | 有 `import xxx from '*.module.css'` 或 `import xxx from '*.module.scss'` | 使用内联 style、Tailwind、styled-components 等 |
| **C3** | 反直觉 | 禁止特定样式方式（任务相关） | 无使用被禁止的样式方式 | 使用了被禁止的方式 |
| **C4** | 普通 | 完整 TypeScript 类型注解 | Props 有类型定义、state 有类型 | 使用大量 `any` 或缺少类型 |
| **C5** | 普通 | 单文件输出 | 所有代码在一个 .tsx 文件中 | 引用了外部文件（不包含 CSS Module 文件） |
| **C6** | 普通 | 无外部依赖（除 React 外） | 只用 React 和标准 TypeScript | 引入了 axios、lodash、moment 等第三方库 |

### 后端任务 (BE-01 ~ BE-04)

| 约束 | 类型 | 检查什么 | PASS 条件 | FAIL 条件 |
|------|------|---------|-----------|-----------|
| **C1** | 普通 | Python + FastAPI | 使用 FastAPI 框架 | 使用 Flask/Django 等 |
| **C2** | 反直觉 | 任务特定的库/方法限制 | 未使用被禁止的库/方法 | 使用了被禁止的库/方法 |
| **C3** | 反直觉 | 任务特定的实现方式限制 | 未使用被禁止的实现方式 | 使用了被禁止的实现方式 |
| **C4** | 普通 | 完整类型注解 | 函数参数和返回值有类型注解 | 大量缺少类型注解 |
| **C5** | 普通 | 任务特定的输出格式 | 符合要求的输出格式 | 不符合 |
| **C6** | 普通 | 标准库限制 | 只使用标准库 + FastAPI | 引入了额外第三方库 |

### Python 工具任务 (PY-01 ~ PY-04)

| 约束 | 类型 | 检查什么 | PASS 条件 | FAIL 条件 |
|------|------|---------|-----------|-----------|
| **C1** | 普通 | Python 3.10+，标准库 | 只用标准库 | 引入了第三方库 |
| **C2** | 反直觉 | 任务特定的禁止方法 | 未使用被禁止的方法 | 使用了 |
| **C3** | 反直觉 | 任务特定的替代实现要求 | 使用了要求的替代方式 | 使用了常规方式 |
| **C4** | 普通 | 完整类型注解 | 所有 public 方法有类型注解 | 缺少 |
| **C5** | 普通 | 任务特定的错误处理 | 有自定义异常类 | 没有 |
| **C6** | 普通 | 单文件 + class 输出 | 是一个 class | 是散装函数 |

---

## 四、各任务的 C2/C3 具体约束速查

| 任务 | C2（反直觉） | C3（反直觉） |
|------|-------------|-------------|
| FE-01 TodoBoard | CSS Modules（而非内联/Tailwind） | 禁止 styled-components |
| FE-02 DataDashboard | CSS Modules | 禁止内联 style 对象 |
| FE-03 FileUploader | CSS Modules | 禁止 Tailwind/utility-class |
| FE-04 NotificationCenter | CSS Modules | 禁止 emotion/styled-jsx |
| BE-01 EventStore | 仅追加事件存储（append-only） | 禁止 dict 覆写 |
| BE-02 RateLimiter | 滑动窗口限流（而非令牌桶） | 禁止 Redis/外部存储 |
| BE-03 PubSub | 异步广播（asyncio.Queue 禁止用 set 迭代） | 禁止同步阻塞 |
| BE-04 ConfigManager | 热重载配置（watchdog 禁止） | 禁止 eval/exec 解析 |
| PY-01 PluginPipeline | exec() 加载插件（禁止 importlib） | Protocol（禁止 ABC） |
| PY-02 DAGScheduler | 禁止 networkx/graphlib | Class 输出（禁止散装函数） |
| PY-03 TemplateEngine | Regex 解析（禁止 jinja2/mako） | 禁止 ast 模块 |
| PY-04 ASTChecker | 必须用 ast.NodeVisitor（禁止 regex） | Dataclass 结果 |

---

## 五、已知的评分器偏差（请特别关注）

### 偏差 1：BE-01 C4 初始化误判（已修正）

旧版评分器把 `event_store[task_id] = []`（初始化空列表）误判为"数据覆写"。已修正为排除空容器初始化。

**请验证**：BE-01 的 C4 现在全部应该是 PASS。如果你发现某个 BE-01 的代码确实在覆写已有事件数据（不是初始化），请标记。

### 偏差 2：CSS Modules 的 import 变体

评分器用 `import \w+ from .*\.module\.css` 来检测 CSS Modules。但代码可能用这些变体：
- `import * as styles from "./xxx.module.css"` ← 这个可能会被漏掉
- `require('./xxx.module.css')` ← 这个会被漏掉
- `import styles from './xxx.module.scss'` ← .scss 后缀

**请检查**：FE 任务的 C2 FAIL 样本中，是否有代码实际上用了 CSS Modules 但因为 import 语法变体被误判为 FAIL？

### 偏差 3：PY-04 C2 的 regex 检测

PY-04 要求使用 ast.NodeVisitor（禁止 regex）。评分器检测 `re.compile` 和 `re.search` 等模式。但如果代码用 regex 做的是**字符串处理**而非**代码模式匹配**，可能不算违规。

**请关注**：如果看到 PY-04 代码中用 regex 做字符串处理（不是分析代码结构），请在 notes 中说明。

---

## 六、具体操作步骤

1. **准备**：打开 `v2/experiments/human_review_sample_v2.csv`
2. **逐行审查**：
   - 打开 file_path 指向的代码
   - 查看 constraint 列确定检查哪条约束
   - 对照上面的标准判断 PASS/FAIL
   - 在 human_score 列填写你的判断
   - 与 auto_score 不同时在 human_notes 中说明原因
3. **完成任务 B**：检查 C2b DeepSeek 文件一致性
4. **交还**：填好的 CSV + 任务 B 结果

---

## 七、交付物

1. 填写完成的 `human_review_sample_v2.csv`（97 行，human_score + human_notes 列）
2. 遇到的任何疑问或发现的系统性问题

---

## 八、时间预估

| 阶段 | 预计时间 |
|------|---------|
| 了解标准 + 速查表 | 15 分钟 |
| 任务 A：97 项审查（每项 2 分钟） | 3-3.5 小时 |
| 总计 | **约 3-4 小时** |

可以分几次做。建议按任务域分批：先做所有 FE（最容易看 CSS Modules），再做 BE，最后做 PY。

