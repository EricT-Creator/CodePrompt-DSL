# CodePrompt-DSL v2 实验设计：Paper-Ready 版本

> **状态**：设计稿，尚未执行  
> **目标**：按正式会议可审标准重建实验框架  
> **日期**：2026-03-31  
> **作者**：erichztang + 砚（AI 研究搭子）

---

## 一、研究问题

### RQ1

对于代码生成中的显式工程约束，紧凑 Prompt Header 是否能在不显著降低任务成功率的前提下降低输入成本？

### RQ2

这种收益是否受**模型能力层级（model tier）**、**任务类型（task domain）**和**Header 编码风格（encoding style）**的影响？

---

## 二、论文贡献定位

### Contribution 1
提出一种面向代码生成显式工程约束的**紧凑 Prompt Header 编码框架**，将高频、闭集、可枚举的约束与开放业务需求分层处理。

### Contribution 2
构建一个**跨前端 / 后端 / Python 的可执行 benchmark**（60 个任务），用于评估 compact headers 的成本与成功率权衡。

### Contribution 3
发现 compact header 的收益具有明显的 **model-tier sensitivity**；英文紧凑编码通常优于古文高密度编码，后者更多作为 **tokenizer economics 的负对照**。

---

## 三、实验矩阵总览

| 维度 | 内容 | 数量 |
|------|------|------|
| **任务** | Frontend × 20 + Backend × 20 + Python × 20 | 60 |
| **Prompt 变体** | NL / JSON / English Compact / Classical Compact | 4 |
| **模型层级** | Lite × 2 + Mid × 2 + Pro × 2 | 6 |
| **总生成次数** | 60 × 4 × 6 | **1440** |

### 缩减方案（如资源不足）

| 方案 | 任务 | 变体 | 模型 | 总次数 |
|------|------|------|------|--------|
| 全量 | 60 | 4 | 6 | 1440 |
| 最小可发表 | 36（每类 12） | 4 | 3（每档 1） | 432 |
| Pilot（验证管线） | 12（每类 4） | 4 | 3 | 144 |

---

## 四、任务集设计

### 4.1 设计原则

1. 每类 20 个任务，难度分三档：基础（8）/ 中等（8）/ 进阶（4）
2. 每个任务附带**标准化约束 schema**，确保 Header 有清晰的压缩对象
3. 每个任务附带**可执行验证方案**（单测 / 构建检查 / 接口测试）
4. 任务需求描述的复杂度有意覆盖从"一句话能说清"到"需要多步推理"的梯度

### 4.2 三大任务类

#### A. Frontend（20 个）

**技术栈**：React + TypeScript  
**约束字段**：语言、框架、组件形式、样式方案、依赖限制、布局适配、数据来源、输出格式  
**验证方式**：`tsc --noEmit` 编译检查 + AST 结构检查（export default、import 分析）+ 关键 DOM 节点静态检查

| 难度 | 示例任务 | 数量 |
|------|---------|------|
| 基础 | 登录表单、用户卡片、计数器、开关面板 | 8 |
| 中等 | 购物车、聊天界面、数据表格、Markdown 编辑器 | 8 |
| 进阶 | 拖拽排序列表、虚拟滚动表格、实时协作白板、多步表单向导 | 4 |

#### B. Backend（20 个）

**技术栈**：两选一——FastAPI (Python) 或 Express (TypeScript)  
**约束字段**：语言、框架、输出形式（单文件 / 单模块）、依赖限制、认证方式、数据格式、是否含测试  
**验证方式**：启动服务 + HTTP 请求测试（状态码 + 响应结构 + 边界条件）

| 难度 | 示例任务 | 数量 |
|------|---------|------|
| 基础 | CRUD API、健康检查、JSON 响应格式化 | 8 |
| 中等 | 分页查询、JWT 认证流程、文件上传接口 | 8 |
| 进阶 | WebSocket 聊天服务、限流中间件、批量导入接口 | 4 |

#### C. Python Scripts（20 个）

**技术栈**：纯 Python 3.12+  
**约束字段**：语言版本、输出形式（CLI / 函数 / 类）、依赖限制（仅标准库 / 允许指定库）、是否含 docstring、是否含单测  
**验证方式**：`python -m pytest` 跑单测 + `mypy --strict` 类型检查（如要求类型注解）

| 难度 | 示例任务 | 数量 |
|------|---------|------|
| 基础 | CSV 解析器、JSON 转换器、文件批量重命名、正则提取器 | 8 |
| 中等 | CLI 参数解析工具、日志分析脚本、简易 HTTP 客户端、配置文件合并器 | 8 |
| 进阶 | 并发下载器、DAG 任务调度器、简易模板引擎、AST 代码检查器 | 4 |

### 4.3 标准化约束 Schema

每个任务定义为一个 JSON 文件：

```json
{
  "task_id": "FE-01",
  "domain": "frontend",
  "difficulty": "basic",
  "name": "LoginForm",
  "description_en": "Build a login form with email and password fields, validation, and error messages.",
  "description_zh_classical": "作登入表，含邮密二栏、校验及误示。",
  "constraints": {
    "language": "TypeScript",
    "framework": "React",
    "form": "single_file_component",
    "style": "tailwind",
    "dependencies": "no_external",
    "layout": "mobile_first",
    "data": "mock",
    "output": "code_only",
    "tests": false,
    "comments": false
  },
  "verification": {
    "type": "frontend_build",
    "checks": ["tsc_compile", "export_default", "no_banned_imports"],
    "functional_checks": ["has_form_element", "has_input_email", "has_input_password", "has_submit_button", "has_error_display"]
  }
}
```

> **砚的说明**：v1 的一个核心问题是功能检测靠单一关键词（如 `lightbox`、`paginat`），这在 v2 中必须改掉。`functional_checks` 应该基于 AST / DOM 结构检查而非字面字符串匹配。详见第六节。

---

## 五、Prompt 变体设计

### 5.1 四组变体

| 组别 | 标识 | 描述 | 作用 |
|------|------|------|------|
| **A** | NL | 纯自然语言（英文） | 基线 |
| **B** | JSON | 自然语言 + JSON 格式约束 | 结构化对照 |
| **C** | Compact | 自然语言 + 英文紧凑 Header | **主方法** |
| **D** | Classical | 自然语言 + 古文高密度 Header | 负对照 / tokenizer 经济学探针 |

### 5.2 各组模板

#### A 组（NL 基线）

```
Write a {language} {task_type} using {framework}.
It should be a {form}. Use {style} for styling.
Do not use any external libraries{except_clause}.
{layout_instruction}. {data_instruction}.
Only output code, no explanations.

{task_description_en}
```

#### B 组（JSON Spec）

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

#### C 组（English Compact Header）

```
===CODE_SPEC===
[L]{lang}[S]{stack}[F]{form}[Y]{style}[D]{dep}[M]{layout}[DT]{data}[O]CODE
===REQ===
{task_description_en}
```

#### D 组（Classical Compact Header）

```
===码制===
[语]{lang}[架]{stack}[式]{form}[样]{style}[依]{dep}[排]{layout}[数]{data}[出]纯码
===需===
{task_description_zh_classical}
```

### 5.3 关键设计决策

**为什么加 JSON 组（B 组）？**

v1 只有 NL / Compact / Classical 三组。Reviewer 很可能会问：

> "为什么不直接用 JSON 格式传约束？你的 compact header 比 JSON 好在哪？"

加上 B 组就能正面回答这个问题：
- JSON 同样是结构化的，但 token 开销更高（大量括号、引号、冒号）
- 如果 Compact 在 token 成本上优于 JSON，且成功率相当，就说明 Header 的压缩设计有独立价值
- 如果 JSON 和 Compact 成功率相同但 JSON 更贵，这是一个 clean result

### 5.4 需求描述部分的处理

| 组别 | 约束部分 | 需求描述部分 |
|------|---------|-------------|
| A (NL) | 英文自然语言 | 英文自然语言 |
| B (JSON) | JSON | 英文自然语言 |
| C (Compact) | 英文紧凑 Header | 英文自然语言 |
| D (Classical) | 古文 Header | **古文需求描述** |

> **砚的说明**：D 组的需求描述用古文，这是有意为之。v1 的发现表明"闭集约束"压缩后基本无损，真正导致差异的是"开放需求"部分。如果 D 组仅 Header 用古文而需求用英文，就无法测出古文在开放语义上的影响。但这也意味着 D 组同时变了两个变量（Header 编码 + 需求语言），在分析中需要做 ablation 讨论。

---

## 六、评估体系（三层）

### 6.1 Layer 1：可执行评估（主指标）

这是最硬的一层，不依赖任何主观判断。

| 任务类型 | 验证方式 | Pass 判定 |
|---------|---------|----------|
| Frontend | `tsc --noEmit` 编译通过 | 无编译错误 |
| Backend (FastAPI) | `uvicorn` 启动 + `httpx` 请求测试 | 服务启动 + 测试全通过 |
| Backend (Express) | `tsc --noEmit` + `supertest` 请求测试 | 编译通过 + 测试全通过 |
| Python | `python -m pytest` 跑预写单测 | 测试全通过 |

**主指标：Pass@1**
- 代码第一次生成后，直接运行验证
- 通过 = 1，不通过 = 0
- 不做重试，不做修正

> **砚的说明**：v1 用的是 0-5 分制，维度拆分后实际区分度主要在 features 维度，其他维度近乎无差异。v2 改用 Pass@1 二元判定，更简洁，更不容易被 reviewer 质疑"你的评分维度权重怎么定的"。

### 6.2 Layer 2：约束遵循评估（规则检查）

每个任务的约束用程序化方式逐条检查：

| 检查项 | 检查方式 | 适用范围 |
|--------|---------|---------|
| 语言正确 | 文件后缀 + AST 解析 | 全部 |
| 框架正确 | import 语句分析 | Frontend / Backend |
| 单文件 | 文件计数 | 全部 |
| 无禁止依赖 | import/require 语句 vs 黑名单 | 全部 |
| 样式方案 | AST className 分析（Tailwind）/ style 属性检查 | Frontend |
| 输出格式 | 是否包含非代码内容（解释文本检测） | 全部 |
| 导出形式 | export default 检查 | Frontend |
| 类型注解 | TypeScript AST 检查（有无显式类型） | TS 任务 |

**指标：Constraint Compliance Rate (CCR)**
- 每个任务有 N 条约束
- CCR = 通过的约束数 / 总约束数
- 汇总时报 mean CCR ± std

> **砚的说明**：v1 的 techStack 检测依赖 `import React` 和 `: React.FC`，这在 React 17+ JSX runtime 下会产生误判。v2 的 AST 检查应该认 `.tsx` 后缀 + TypeScript AST 中是否存在类型节点，而不是查特定字符串。

### 6.3 Layer 3：功能完整性（LLM Judge 辅助）

仅用于 Pass@1 = 0 时的**失败原因分类**，以及需要语义判断的功能完整度评估。

**LLM Judge 不参与主指标计算。**

用法：
1. 对 Pass@1 = 0 的生成结果，用 LLM judge 分类失败原因：
   - 语法错误
   - 缺少核心功能
   - 约束违反
   - 输出格式错误
   - 其他
2. 对 Pass@1 = 1 但功能覆盖不完整的情况，用 LLM judge 做 0-3 分功能完整度评分：
   - 0 = 完全缺失
   - 1 = 部分实现
   - 2 = 基本完整
   - 3 = 完整且合理

**LLM Judge 选择**：使用与被测模型不同的模型做 judge（推荐 GPT-5.4 或 Claude Opus 4.6）。

> **砚的说明**：v1 的功能评估完全靠关键词匹配，这是被 v1 探索性分析里反复指出的硬伤。v2 把功能评估降级为辅助层，主指标改为可执行验证，这是最大的方法论升级。

---

## 七、模型选择

### 7.1 分层原则

| 层级 | 定义 | 要求 |
|------|------|------|
| **Lite / Fast** | 轻量/快速推理模型 | 每档至少 2 个 |
| **Mid / Instruct** | 中档指令遵循模型 | 每档至少 2 个 |
| **Pro / Reasoning** | 顶级推理模型 | 每档至少 2 个 |

### 7.2 候选模型池

> 以下为建议，最终选择需根据实验时 API 可用性和成本确定。

| 层级 | 候选模型 | 来源 | 备注 |
|------|---------|------|------|
| Lite | Gemini-3.1-Flash-Lite | Google | v1 已测，可直接对比 |
| Lite | DeepSeek-V3.2 | 深度求索 | v1 已测，可直接对比 |
| Mid | Gemini-3.0-Flash | Google | v1 已测 |
| Mid | GLM-5.0-Turbo | 智谱 | v1 已测，中文模型代表 |
| Pro | GPT-5.4 | OpenAI | v1 已测，顶级表现 |
| Pro | Gemini-3.0-Pro | Google | v1 全满分 |

### 7.3 与 v1 的可比性

保留至少 3 个 v1 已测模型（每层级 1 个），可以做 **v1→v2 的纵向对比**，回答"新实验框架下结论是否一致"。

### 7.4 砚的补充建议

**关于中文模型**：v1 发现 GLM/Kimi/MiniMax 在 D 组 Classical 上比 Claude 更稳。如果论文要讨论"古文 Header 是否对中文训练数据模型更友好"，至少需要 Mid 层保留一个中文模型（GLM 或 Kimi）。当前方案里 GLM 在 Mid 层，这没问题。

**关于 Kimi 和 MiniMax**：如果模型数量可以扩到 8 个，建议在 Mid 层加 Kimi-K2.5，以便做"中文模型一致性"分析。如果只能 6 个，就先不加。

### 7.5 实验平台：WorkBuddy（腾讯云代码助手）

#### 平台事实声明

本实验的所有代码生成均通过 **WorkBuddy**（腾讯云代码助手桌面版，https://copilot.tencent.com/work/ ）完成。WorkBuddy 支持在界面中切换不同的大语言模型。

#### 调用方式调研结论

根据公开资料的调研（2026-03-31），WorkBuddy 对模型的调用方式存在**两种路径**：

**路径 1：内置模型**
- WorkBuddy 桌面版自带一组内置模型，用户通过 Credits 额度使用
- **调用机制未被官方技术文档明确披露**
- 已知的事实：两款产品"均搭载腾讯安全网关"（来源：腾讯云开发者社区对比文）
- 因此存在一个**不可排除的可能性**：内置模型的请求经过腾讯的 API 网关 / 代理层转发到各模型厂商，网关层可能注入了 system prompt（例如安全合规指令、输出格式约束等）

**路径 2：自定义模型（用户自行配置 API Key）**
- 用户可通过 `~/.workbuddy/models.json` 配置自定义模型
- 此时使用用户自己的 API Key + 原生 API 端点
- 配置方式为标准 OpenAI 兼容格式
- 此路径下，**模型调用更接近原生 API**，但仍经过 WorkBuddy 客户端的 prompt 组装流程

#### 这对实验意味着什么

| 因素 | 影响 | 处理方式 |
|------|------|---------|
| **腾讯安全网关可能注入 system prompt** | 可能影响模型的输出行为（如拒绝生成某些内容、添加安全声明等） | 在论文 Threats to Validity 中声明 |
| **WorkBuddy 的 prompt 组装** | 用户输入的 prompt 可能被 WorkBuddy 包裹在更大的 system prompt / instruction 模板中 | 在论文 Methodology 中声明实验平台，并说明"所有变体的 prompt 都经过相同的平台路径，因此平台中间层的影响对四组变体是等价的" |
| **无法确认是否有模型微调** | 如果腾讯对内置模型做了微调，输出可能不完全等价于原生 API | 在论文中声明"本实验测量的是通过 WorkBuddy 平台访问的模型表现，不声称等价于直接 API 调用" |

#### 论文中的推荐表述

> **Experimental Platform.** All code generations were conducted through WorkBuddy (Tencent Cloud CodeBuddy Desktop, v{版本号}), a desktop AI agent that supports multiple LLM backends. Models were accessed via WorkBuddy's built-in model switching interface. While WorkBuddy routes requests through Tencent's API gateway, all four prompt variants were submitted through the identical platform pipeline, ensuring that any platform-level prompt wrapping or system instructions affect all conditions equally. We note that WorkBuddy's intermediary layer may differ from direct API access; our results reflect model performance as experienced through this specific platform.

#### 是否需要担心这个问题？

**短回答：不需要太担心，但必须声明。**

原因：
1. **四组变体走的是同一条管线**——如果有 system prompt 注入，它对 A/B/C/D 四组的影响是相同的。你比较的是"组间差异"，不是"绝对表现"。
2. **同一模型在平台上的表现差异，是一个 constant offset**——它不会改变"Compact 比 NL 省了多少 token"这个相对结论。
3. **但 reviewer 会问**：所以你需要在 Threats to Validity 里提前说清楚。

---

## 八、指标体系

### 8.1 主指标

| 指标 | 定义 | 用途 |
|------|------|------|
| **Pass@1** | 首次生成是否通过可执行验证 | RQ1 核心指标 |
| **Input Token Count** | Prompt 的 token 数 | RQ1 成本指标 |
| **Constraint Compliance Rate (CCR)** | 约束逐条通过率 | RQ1 约束遵循指标 |

### 8.2 辅助指标

| 指标 | 定义 | 用途 |
|------|------|------|
| **Functional Completeness (0-3)** | LLM judge 功能完整度评分 | 深入分析 |
| **Output Token Count** | 生成代码的 token 数 | 成本分析 |
| **Failure Category** | LLM judge 失败分类 | 错误模式分析 |

### 8.3 综合成本指标

**Total Token Cost (TTC)**

```
TTC = input_tokens × input_price + output_tokens × output_price
```

如果实验中允许 retry（主实验不允许，但可以做附加实验）：

```
TTC_retry = Σ(input_tokens_i × input_price + output_tokens_i × output_price) for i in 1..n_attempts
```

> **砚的说明**：这个指标很重要。v1 只算了 input token 节省，但实际上如果 compact header 导致 Pass@1 下降、需要更多重试，总账可能不省反贵。TTC 可以正面回应这个质疑。不过**主实验建议不做 retry**，保持 Pass@1 的纯粹性；retry 分析可以放到附加实验或讨论章节。

---

## 九、统计检验方案

### 9.1 主检验

| 比较 | 方法 | 理由 |
|------|------|------|
| Pass@1 across prompt variants | **McNemar's test** / **Cochran's Q test** | 二元配对数据 |
| CCR across prompt variants | **Friedman test** + **Nemenyi post-hoc** | 配对、非正态分布 |
| Input token count across variants | **配对 t-test** 或 **Wilcoxon signed-rank** | 连续变量配对 |

### 9.2 报告要求

每个比较必须报告：
- **Mean ± Std**
- **95% CI**（bootstrap，B=10000）
- **Effect size**（Cohen's d 或 Cliff's delta）
- **p-value**（Bonferroni 校正后）

### 9.3 RQ2 的交互分析

| 分析 | 方法 |
|------|------|
| Prompt variant × Model tier 交互 | **Two-way ANOVA** 或 **Aligned Rank Transform** |
| Prompt variant × Task domain 交互 | 同上 |
| 三因素交互 | 分层报告 + 可视化（热力图） |

> **砚的说明**：v1 只做了 paired t-test 和 Cohen's d。v2 因为是多组比较（4 个 prompt variant），需要先做全局检验（Cochran's Q / Friedman），再做 post-hoc 成对比较。不能直接跑 6 对 t-test 然后不校正。

---

## 十、结果呈现模板

### 10.1 主结果表（Table 1）

| Model | Tier | NL Pass@1 | JSON Pass@1 | Compact Pass@1 | Classical Pass@1 | NL Tokens | Compact Tokens | Δ Tokens |
|-------|------|-----------|-------------|----------------|-----------------|-----------|----------------|----------|
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 10.2 按任务域分拆（Table 2）

| Domain | NL Pass@1 | JSON Pass@1 | Compact Pass@1 | Classical Pass@1 | Sig. |
|--------|-----------|-------------|----------------|-----------------|------|
| Frontend | ... | ... | ... | ... | ... |
| Backend | ... | ... | ... | ... | ... |
| Python | ... | ... | ... | ... | ... |

### 10.3 约束遵循率（Table 3）

| Constraint | NL CCR | JSON CCR | Compact CCR | Classical CCR |
|------------|--------|----------|-------------|---------------|
| Language | ... | ... | ... | ... |
| Framework | ... | ... | ... | ... |
| Dependencies | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |

### 10.4 统计检验汇总（Table 4）

| Comparison | Δ Mean | 95% CI | Effect Size | p-value |
|------------|--------|--------|-------------|---------|
| NL vs Compact | ... | ... | ... | ... |
| NL vs JSON | ... | ... | ... | ... |
| NL vs Classical | ... | ... | ... | ... |
| Compact vs JSON | ... | ... | ... | ... |

---

## 十一、执行分阶段计划

### Phase A：设计与基础设施（1-2 周）

| 步骤 | 产出 | 优先级 |
|------|------|--------|
| A1. 定义 60 个任务的完整 JSON schema | `v2/tasks/` 目录 | P0 |
| A2. 为每个任务写可执行验证脚本 | `v2/eval/` 目录 | P0 |
| A3. 定义 4 种 prompt 模板 + 自动填充脚本 | `v2/prompts/` 目录 | P0 |
| A4. 搭建自动化 pipeline：生成 → 保存 → 验证 → 记录 | `v2/runner/` 脚本 | P0 |
| A5. 确定统计分析脚本 | `v2/analysis/` 目录 | P1 |
| A6. 产出实验执行手册 | `v2/EXPERIMENT_RUNBOOK.md` | P0 |

### Phase B：Pilot 验证（3-5 天）

| 步骤 | 产出 |
|------|------|
| B1. 选 12 个任务（每类 4 个） | pilot 子集 |
| B2. 跑 12 × 4 × 9 = 432 次生成 | pilot 结果 |
| B2.5 **每个模型生成完后立即执行交叉审查** | 审查日志 + 汇总报告 |
| B3. 对关键子集跑 3 次，验证 Pass@1 一致性 | 一致性报告 |
| B4. 验证 pipeline + 审核流程正确性 | 调试报告 |
| B5. 确认评估指标是否有效区分 | pilot 分析 |

### Phase C：全量实验（1-2 周）

| 步骤 | 产出 |
|------|------|
| C1. 跑 60 × 4 × 9 = 2160 次生成（每个模型完成后立即审查） | 全量结果 + 审查报告 |
| C2. 运行三层评估 | 评估数据 |
| C3. 独立审核脚本交叉验证 | 审核报告 |
| C4. 统计分析 | 分析结果 |
| C5. 生成结果表和可视化 | 论文素材 |

### Phase D：论文写作

| 章节 | 依赖 |
|------|------|
| Introduction + Related Work | 可在 Phase A 并行 |
| Methodology | Phase A 完成后 |
| Results | Phase C 完成后 |
| Discussion + Conclusion | Phase C 分析完成后 |

---

## 十二、v1 / v2 隔离与版本管理

### 12.1 目录结构

```
/Users/erichztang/Downloads/古文运动/
├── experiment_data/              # v1 数据（只读，不动）
├── v2/                           # v2 全部新内容
│   ├── EXPERIMENT_RUNBOOK.md     # 实验执行手册（每次切换模型必读）
│   ├── REVIEW_PROTOCOL.md       # 产物审查协议（审查模型必读）
│   ├── TASK_DEFINITIONS.md      # 60 个任务定义
│   ├── PROMPT_TEMPLATES.md      # 4 种 prompt 模板
│   ├── tasks/                    # 60 个任务定义 JSON
│   ├── prompts/                  # 4 种 prompt 模板 + 生成脚本
│   ├── generations/              # 生成结果
│   │   └── {model_name}/
│   │       ├── A/                # NL 组
│   │       ├── B/                # JSON 组
│   │       ├── C/                # Compact 组
│   │       └── D/                # Classical 组
│   ├── eval/                     # 评估脚本
│   ├── results/                  # 评分结果 JSON
│   ├── audit/                    # 审查日志与汇总报告
│   │   ├── review_log.jsonl      # 逐文件审查记录（append-only）
│   │   └── review_summary_*.md   # 各模型的审查汇总
│   ├── logs/                     # 执行日志（append-only）
│   └── analysis/                 # 统计分析脚本和输出
├── EXPERIMENT_V2_DESIGN.md       # v2 实验设计（本文件）
├── RELATED_WORK_SURVEY.md        # 文献调研
└── README.md                     # 项目说明
```

### 12.2 隔离原则

1. **v1 数据只读**：`experiment_data/` 目录下的任何文件不做修改、不做删除
2. **v2 数据全部在 `v2/` 下**：新任务、新生成、新评估、新日志全在这里
3. **论文中 v1 作为"preliminary study"引用**：v1 的发现作为动机和先验知识，v2 作为正式实验
4. **Git 管理**：v1 和 v2 的提交历史自然隔离

---

## 十三、模型选择更新：加入三个争议模型

### 13.1 更新后的完整模型列表

| 层级 | 模型 | 来源 | v1 状态 | v2 角色 |
|------|------|------|---------|---------|
| **Lite** | Gemini-3.1-Flash-Lite | Google | v1 可信 | 主模型 |
| **Lite** | DeepSeek-V3.2 | 深度求索 | v1 可信 | 主模型 |
| **Mid** | Gemini-3.0-Flash | Google | v1 可信 | 主模型 |
| **Mid** | GLM-5.0-Turbo | 智谱 | v1 可信 | 主模型 |
| **Pro** | GPT-5.4 | OpenAI | v1 可信 | 主模型 |
| **Pro** | Gemini-3.0-Pro | Google | v1 可信 | 主模型 |
| **争议** | Claude-Haiku-4.5 | Anthropic | v1 不可信 | 重新测试 |
| **争议** | Hunyuan-2.0-Thinking | 腾讯 | v1 不可信 | 重新测试 |
| **争议** | Hunyuan-2.0-Instruct | 腾讯 | v1 谨慎保留 | 重新测试 |

**总计：9 个模型 × 4 变体 × 60 任务 = 2160 次生成**

### 13.2 争议模型的"作弊"防护方案

v1 中 claude-haiku-4.5、hunyuan-2.0-thinking、hunyuan-2.0-instruct 出现了以下问题：
- 生成模板化/复制性代码
- 不理解实验要求
- 输出与预期格式严重不符

**v2 的处理方案：不做高阶模型 orchestration，而是从 prompt 本身入手。**

#### 为什么不用高阶模型做"中间翻译"

如果用 GPT-5.4 先理解需求再转交给 Haiku 执行，会引入两个问题：
1. **不公平**：其他模型直接看 prompt，Haiku 看的是 GPT-5.4 的"翻译版"，这不是同一个实验条件
2. **不可复现**：GPT-5.4 的翻译本身有随机性，第三方无法复现

#### 替代方案：统一的 standardized instruction preamble

给**所有模型**（不只是争议模型）添加一个标准化的指令前导（preamble）：

```
You are a code generation assistant participating in a controlled experiment.
Your task is to generate code that EXACTLY follows the specification below.

RULES:
1. Output ONLY code. No explanations, no markdown fences, no comments about the task.
2. The code must be a complete, self-contained file that can run/compile as-is.
3. Follow ALL constraints specified in the header or description.
4. Do NOT copy from any template. Generate fresh code for this specific task.
5. If you are unsure about any requirement, implement your best interpretation.

---
```

这个 preamble **四组变体都加**，放在每个 prompt 的最前面。因此：
- 不影响组间比较（四组都有相同的 preamble）
- 减少模型"偷懒"或"不理解格式"的概率
- 在论文里声明 "a standardized instruction preamble was prepended to all prompts across all conditions"

#### 如果争议模型仍然"作弊"怎么办

**那本身就是一个有效的实验结果。** 审计脚本会自动检测以下异常模式：

1. **重复内容检测**：不同任务生成了内容完全相同的代码（hash 碰撞）
2. **模板化检测**：输出仅在变量名或注释上有微小差异
3. **格式违反检测**：输出包含非代码内容（解释文字、markdown 围栏等）
4. **空输出检测**：输出为空或极短（< 50 字符）

如果某模型在多个任务上触发上述异常，审计报告会将其标记为：

> **"Model {name} failed to produce valid, independent outputs for {N}/{total} task-variant combinations. This model is classified as unable to follow structured constraint instructions at the required level."**

这个结论本身就是对 RQ2 的一个有价值的回答——compact header 的有效性确实依赖模型的基础指令遵循能力。

论文中可以写：

> "Models in the Lite tier and certain Instruct-tuned models failed to produce valid outputs even with explicit instructions, suggesting that compact header comprehension requires a minimum level of instruction-following capability."

---

## 十四、实验合规与留痕制度

### 14.0 双模型交叉审查制度（2026-03-31 新增）

#### 审查分工

| 审查模型 | 审查范围 | 原因 |
|---------|---------|------|
| **Gemini-3.0-Pro** | 除 Gemini-3.0-Pro 以外的全部 8 个模型 | v1 全满分模型，审查能力最强 |
| **GPT-5.4** | 仅审查 Gemini-3.0-Pro 的产物 | v1 第二名，保证立场独立性 |

两个审查模型执行**完全相同的审查流程和标准**，定义在 `v2/REVIEW_PROTOCOL.md` 中。

#### 审查时机

**每个模型的代码生成全部完成后，立即切换到审查模型执行审查。**

不等到所有模型跑完再统一审查。这样做的好处：
1. 如果发现系统性问题（如 prompt 模板错误），可以在早期发现并修正
2. 避免最后集中审查时遗漏，导致需要全部重跑

#### 执行-审查循环

```
模型X生成 → 切换到审查模型 → 审查模型X的产物 → 产出审查报告 → 进入下一个模型
```

#### 审查内容概要

审查协议包含 12 项检查（R1-R12），涵盖：
- **文件完整性**（R1-R2）
- **语言和框架正确性**（R3-R4）
- **约束遵循**（R5-R9）
- **功能完整性**（R10，0-3 分制）
- **独立性验证**（R11-R12，检测复制/模板化）

详见 `v2/REVIEW_PROTOCOL.md`。

#### 审查输出

| 输出 | 文件位置 | 格式 |
|------|---------|------|
| 逐文件审查记录 | `v2/audit/review_log.jsonl` | JSONL，逐条追加 |
| 模型级汇总报告 | `v2/audit/review_summary_{model}.md` | Markdown |

#### 操作者触发审查的标准化 prompt

定义在 `v2/EXPERIMENT_RUNBOOK.md` 第九节。操作者每次触发审查时使用纯自然语言模板，与生成指令模板的设计原则一致。

#### 论文中的体现

在 Methodology 节声明：

> *"To ensure evaluation objectivity, we employed a cross-model review protocol. Gemini-3.0-Pro reviewed outputs from all other models, while GPT-5.4 independently reviewed Gemini-3.0-Pro's outputs. Both reviewers followed an identical 12-point review protocol covering constraint compliance, functional completeness, and output independence. Reviews were conducted immediately after each model's generation phase, enabling early detection of systematic issues."*

### 14.1 核心原则：Append-Only，禁止删除

| 规则 | 说明 |
|------|------|
| **禁止删除任何实验记录** | 包括生成的代码、评估结果、日志条目 |
| **出错不删，只增加分支** | 错误记录标注 `[ERROR]`，重试记录标注 `[RETRY-N]` |
| **每步留痕** | 每次生成、评估、审核都写入对应日志 |
| **日志为 append-only** | 只追加，不修改已有内容 |

### 14.2 日志结构

#### 生成日志（`v2/logs/generation_log.jsonl`）

每次代码生成追加一条：

```json
{
  "timestamp": "2026-03-31T11:00:00Z",
  "model": "gpt-5.4",
  "task_id": "FE-01",
  "variant": "C",
  "prompt_hash": "sha256:abc123...",
  "output_file": "v2/generations/gpt-5.4/C/FE-01_LoginForm.tsx",
  "output_hash": "sha256:def456...",
  "status": "success",
  "notes": ""
}
```

#### 评估日志（`v2/logs/evaluation_log.jsonl`）

每次评估追加一条：

```json
{
  "timestamp": "2026-03-31T11:05:00Z",
  "model": "gpt-5.4",
  "task_id": "FE-01",
  "variant": "C",
  "evaluator": "auto_pipeline_v2",
  "pass_at_1": true,
  "ccr": 1.0,
  "constraint_details": {"language": 1, "framework": 1, "dependencies": 1, ...},
  "notes": ""
}
```

#### 审核日志（`v2/audit/audit_log.jsonl`）

独立审核脚本的输出：

```json
{
  "timestamp": "2026-03-31T12:00:00Z",
  "auditor": "audit_script_v2",
  "scope": "gpt-5.4/C/FE-01",
  "checks": {
    "file_exists": true,
    "hash_matches_generation_log": true,
    "eval_result_consistent": true,
    "no_banned_imports": true
  },
  "verdict": "PASS",
  "notes": ""
}
```

### 14.3 独立审核流程

| 步骤 | 执行者 | 检查内容 |
|------|--------|---------|
| 1. 文件完整性 | `audit_script` | 每个 (model, variant, task) 组合是否都有对应的代码文件 |
| 2. 哈希一致性 | `audit_script` | 代码文件的 SHA-256 是否与 generation_log 中记录的一致（防止事后篡改） |
| 3. 评估一致性 | `audit_script` | 重新运行评估脚本，对比结果是否与 evaluation_log 一致 |
| 4. 约束合规 | `audit_script` | 逐条检查约束是否被正确评估 |
| 5. 异常检测 | `audit_script` | 检测是否有重复文件（不同 task 但内容完全相同 = 疑似复制/模板化） |

**审核脚本独立于生成和评估脚本**，不共享任何状态。

### 14.4 错误处理

```
正常流程：
  生成 → 保存 → 记录日志 → 评估 → 记录日志 → 审核 → 记录日志

出错时：
  生成失败 → 记录 [ERROR] → 重试 → 保存为 [RETRY-1] → 记录日志
                                  → 再失败 → 记录 [ERROR] → 重试 → [RETRY-2]
                                  → 最多 3 次重试
                                  → 3 次都失败 → 记录 [FAILED] → 跳过该组合

所有 ERROR / RETRY / FAILED 记录永久保留，不删除。
```

---

## 十五、模型切换时的上下文保持方案

### 15.1 问题

WorkBuddy 切换模型后，新模型的对话上下文会重置。如果新模型不了解实验设计和合规要求，可能会：
- 生成不符合格式的代码
- 不遵守 append-only 留痕规则
- 不理解 prompt 变体的含义

### 15.2 解决方案：实验执行手册（Runbook）

产出一份独立的 `v2/EXPERIMENT_RUNBOOK.md`，包含：
1. 实验背景和目标（简版）
2. 当前模型的任务指令
3. 输出格式要求
4. 文件命名和保存路径规范
5. 合规留痕规则
6. 禁止事项清单

**每次切换模型后，将 Runbook 全文作为对话的第一条消息发送。**

### 15.3 Runbook 的内容应该包括

```
# 实验执行手册 v2

## 你现在要做什么
你正在参与 CodePrompt-DSL v2 实验。你的任务是根据给定的 prompt 生成代码。

## 关键规则
1. 只输出代码，不输出解释
2. 代码必须是完整的、可独立运行的单文件
3. 严格遵循 prompt 中的所有约束
4. 不要从模板复制，每次生成全新代码
5. 如果不确定某个需求，按你的最佳理解实现

## 文件保存
- 保存路径：v2/generations/{model_name}/{variant}/{task_id}_{task_name}.{ext}
- 文件名格式严格遵循上述模式

## 禁止事项
- 禁止删除任何已生成的文件
- 禁止修改已保存的代码文件
- 禁止跳过任何任务
- 如果出错，重新生成并保存为新文件（标注 RETRY-N）
```

---

## 十六、v1→v2 对照：哪些是继承的，哪些是新的

| 维度 | v1 | v2 | 变化原因 |
|------|----|----|---------|
| 任务数量 | 10 | 60 | Reviewer 会质疑泛化性 |
| 任务类型 | 仅前端 React | 前端 + 后端 + Python | "只对 React 有效"的质疑 |
| Prompt 变体 | 3 (NL/Compact/Classical) | 4 (+JSON) | 需要回答"为什么不用 JSON" |
| 模型数量 | 9 可信 | 9（6 主 + 3 争议重测） | 扩展覆盖，加回争议模型 |
| 评估主指标 | 0-5 分（关键词匹配） | Pass@1（可执行验证） | 关键词匹配太弱 |
| 约束检测 | 字面字符串匹配 | AST / 编译器级别检查 | `import React` 误判问题 |
| 功能检测 | 字面关键词 75% | 可执行单测 + LLM judge 辅助 | `lightbox` / `paginat` 偏置 |
| 统计检验 | 配对 t-test | McNemar / Friedman + post-hoc + CI + effect size | 多组比较 |
| 成本指标 | 仅 input token | Input + Output + TTC | "省 input 不代表总账更优" |
| 留痕制度 | 无 | Append-only + 独立审核 + 哈希校验 | 论文级可复现性 |
| v1/v2 隔离 | 无 | `experiment_data/` 只读，`v2/` 新建 | 可追溯性 |

---

## 十七、砚的补充意见和风险提示

你的建议框架非常扎实，以下几点我完全认同：

1. **RQ 收紧**：从泛泛的"DSL 有没有用"变为两个可证伪的问题，这是论文能不能过审的基础
2. **加 JSON 对照组**：这是最容易被 reviewer 问到的"为什么不用 X"
3. **可执行评估替代关键词匹配**：v1 最大的方法论硬伤，必须改
4. **TTC 总成本指标**：正面回应"省 input 不代表总账更优"
5. **模型分层作为主轴**：v1 里模型选择是"能用什么用什么"，v2 变成有意义的分层设计

### 13.2 我建议额外注意的

#### （1）D 组的 confound 问题

D 组同时改了两个变量：Header 编码（古文）和需求描述语言（古文）。严格来说，如果 D 组表现差，你不能直接归因于"古文 Header 不行"，因为也可能是"古文需求描述不行"。

**建议处理方式**：
- 在论文 Discussion 中明确讨论这个 confound
- 如果有余力，可以加一个 ablation：古文 Header + 英文需求（D'组），但这不是 P0

#### （2）60 个任务的质量控制

60 个任务不是随便凑的。需要确保：
- 每个任务的约束字段不是完全相同的（否则你在测"60 次相同约束"而不是"60 个不同约束配置"）
- 难度标注有客观依据（比如代码行数期望、逻辑分支数）
- 任务描述的长度和复杂度也应该有分布，不要全是一句话或全是长段落

**建议处理方式**：
- 设计一个"约束配置矩阵"，确保 60 个任务覆盖了约束字段的不同组合
- 在论文中报告任务描述的平均 token 数 ± std

#### （3）Backend 任务的框架选择问题

你提了 FastAPI 和 Express 两种。但如果同一个任务既有 FastAPI 版又有 Express 版，那它到底是 1 个任务还是 2 个？

**建议处理方式**：
- Backend 20 个任务统一用一种框架（建议 FastAPI，因为 Python 验证 pipeline 更成熟）
- 如果想测"框架无关性"，可以从 20 个里选 5 个做 FastAPI + Express 双版本，作为附加实验

#### （4）每个任务只跑 1 次的统计功效

1440 次生成听起来很多，但每个具体的 (task, variant, model) 组合只跑了 1 次。如果 Pass@1 有随机性（同一 prompt 给同一模型，两次可能不同），1 次采样的方差会很大。

**建议处理方式**：
- 主实验维持 1 次（论文惯例，也节省成本）
- 但在 pilot 阶段，对 12 个任务子集跑 3 次，计算"**同组合内 Pass@1 的一致性**"
- 如果一致性 > 90%，就说明 1 次采样足够可靠
- 如果一致性低，需要在论文 limitation 里讨论，或增加采样次数

#### （5）Related Work 不能最后再补

你说"先把实验框架打牢，再补文献综述"——方向对，但 related work 不能完全后补。至少在开始写任务定义之前，你需要确认：

- 有没有人已经做过类似的"Prompt 压缩对代码生成的影响"实验
- 有没有现成的 benchmark 可以直接用或对比
- "Prompt Engineering for Code Generation"这个方向的 SOTA 是什么

如果别人已经有一个 50 任务的 benchmark 你不知道，但 reviewer 知道，那就很尴尬。

**建议处理方式**：
- Phase A 并行做一轮 related work 调研
- 重点查 2024-2026 年的 ACL / EMNLP / ICML / NeurIPS 关于 prompt engineering + code generation 的论文

---

## 十八、下一步行动建议

按时间线：

1. **本周**：确认 RQ、贡献定位、模型选择（你已经大致定了）
2. **下周起**：开始 Phase A，先定义 12 个 pilot 任务 + 写对应的验证脚本
3. **Phase A 中**：并行做 related work 调研
4. **Phase B**：跑 pilot，验证 pipeline
5. **Phase C**：全量跑
6. **Phase D**：写论文

最早能出一版可投稿初稿的时间，大概是 Phase A 开始后 **6-8 周**（如果全职推进的话）。

---

*设计稿完成时间：2026-03-31 10:30*  
*待用户确认后进入 Phase A 执行*
