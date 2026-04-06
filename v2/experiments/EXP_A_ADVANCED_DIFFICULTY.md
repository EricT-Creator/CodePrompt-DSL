# EXP-A：进阶难度实验设计

> **实验编号**：EXP-A  
> **目的**：打破 Pilot 阶段 Pass@1 天花板效应（98.2%），增加任务难度以提高 prompt variant 间的区分度  
> **前提**：Pilot 分析发现 12 个基础/中等任务中 9/11 模型达到 100% Pass@1，三因素交叉在 Pro/Mid 层全为 100%，无法支撑统计检验  
> **设计时间**：2026-03-31  
> **状态**：待执行

---

## 一、问题陈述

### 1.1 要解决的具体问题

| # | 问题 | Pilot 数据证据 | 影响 |
|---|------|---------------|------|
| P1 | Pass@1 天花板 | 整体 98.2%，9/11 模型 = 100% | 无法做变体间统计检验 |
| P2 | 三因素交叉无区分 | Pro/Mid 层全 100%，Lite 层差异全来自 DeepSeek 文件缺失 | RQ2 无法回答 |
| P3 | 功能分梯度不足 | 多数模型 FE 域功能分 = 3.0 | R10 在基础任务上也接近天花板 |
| P4 | FE-04 是唯一区分任务 | 88.9% 整体 Pass@1（`plain_css` 反直觉约束） | 说明"反直觉约束"是有效的区分度来源 |

### 1.2 设计目标

- 使 Pro 层模型 Pass@1 降至 70-85% 区间（而非 100%）
- 使 C (Compact) vs A (NL) 在进阶任务上出现可测量的差异（而非全等）
- 使 R10 功能分在进阶任务上出现 0-3 的完整分布（而非集中在 3）
- 使 BE/PY 域的变体克隆在进阶任务上消失（验证"任务复杂度"假说）

---

## 二、任务设计原则

### 2.1 难度梯度框架

基于 FE-04 的成功经验（`plain_css` 约束是唯一产生区分度的设计），提炼以下产生区分度的机制：

| 机制 | 说明 | 预期效果 |
|------|------|---------|
| **反直觉约束** | 约束与模型"默认行为"冲突（如 React 项目要求 plain_css、FastAPI 项目禁用 Pydantic） | 强迫模型主动抑制训练先验，CCR 下降 |
| **约束冲突检测** | Header 和描述中包含矛盾信息，模型需识别并遵循优先级 | 测试模型是否真正阅读 Header |
| **多步约束交叉** | 单个约束不难，但多个约束组合后产生冲突（如 "无外部库" + "需要 JWT 认证"） | 逻辑推理负担增加，弱模型 Pass@1 下降 |
| **输出格式陷阱** | 看似简单但格式要求严格（如"只输出函数体，不要 import 语句"） | 测试模型是否遵循细粒度输出约束 |
| **领域知识壁垒** | 需要特定领域知识的实现（如 DAG 拓扑排序、虚拟滚动窗口计算） | 功能分区分度提高 |

### 2.2 约束层级定义

每个进阶任务的约束分为三层，Header 中必须包含全部三层：

```
Layer 1 - 技术栈（与 Pilot 一致）：语言、框架、样式方案
Layer 2 - 工程约束（新增）：依赖白名单/黑名单、输出格式约束、代码结构约束
Layer 3 - 反直觉约束（新增）：与模型默认行为冲突的约束
```

---

## 三、任务列表

### 3.1 Frontend 进阶任务（FE-05 ~ FE-08）

#### FE-05：DraggableSortList（拖拽排序列表）

| 字段 | 内容 |
|------|------|
| **需求** | 可拖拽排序的列表组件，支持拖放交换、拖拽中视觉反馈、排序结果实时更新 |
| **反直觉约束** | `style=plain_css`（禁止 Tailwind）+ `no_html5_drag`（禁止使用 HTML5 原生 Drag and Drop API，必须用 mouse/touch 事件手动实现） |
| **多步交叉** | 无外部库 + 手动拖拽实现 = 需要从零实现拖拽逻辑 |
| **预期难点** | 模型训练数据中大量使用 `react-beautiful-dnd` 或 HTML5 DnD，禁用后需要纯手写 mouse event handler |
| **功能关键词** | mousedown/touchstart handler, position calculation, placeholder rendering, onDrop reorder, visual feedback |
| **评分锚点** | 3分 = 完整拖放+视觉反馈+正确排序；2分 = 能拖但无反馈/排序偶尔错；1分 = 只有列表无拖拽；0分 = 缺失或不编译 |

#### FE-06：VirtualScrollTable（虚拟滚动表格）

| 字段 | 内容 |
|------|------|
| **需求** | 支持 10000 行数据的虚拟滚动表格，固定表头，可排序列 |
| **反直觉约束** | `no_windowing_lib`（禁止 react-window / react-virtualized）+ `style=css_modules`（禁止 Tailwind 和内联样式） |
| **多步交叉** | 无外部库 + 虚拟滚动 = 需要手动实现窗口化渲染 |
| **预期难点** | 虚拟滚动需要精确计算 scrollTop → visibleRange → offsetY，这不是模型的"默认模板" |
| **功能关键词** | scrollTop calculation, visible row range, overscan buffer, fixed header, column sort, absolute positioning |
| **评分锚点** | 3分 = 滚动流畅+固定表头+排序工作；2分 = 能滚动但有闪烁/表头不固定；1分 = 全量渲染无虚拟化；0分 = 缺失或不编译 |

#### FE-07：CollaborativeWhiteboard（实时协作白板）

| 字段 | 内容 |
|------|------|
| **需求** | Canvas 绘画白板，支持画笔/橡皮擦/颜色选择/撤销重做/清除画布 |
| **反直觉约束** | `no_canvas_lib`（禁止 fabric.js / konva 等 canvas 库）+ `state=useReducer`（禁止 useState，必须用 useReducer 管理全部状态） |
| **多步交叉** | 无 canvas 库 + useReducer only = 需要手动管理 Canvas 2D API + action dispatch |
| **预期难点** | Canvas 绘画的 mouse event → path recording → undo stack 是非平凡的状态管理任务 |
| **功能关键词** | canvas 2d context, mousedown/mousemove/mouseup, path array, undo stack, redo stack, eraser mode, color picker |
| **评分锚点** | 3分 = 画笔+橡皮+颜色+撤销重做全部工作；2分 = 能画但缺撤销或橡皮；1分 = canvas 存在但不能画；0分 = 缺失 |

#### FE-08：MultiStepFormWizard（多步表单向导）

| 字段 | 内容 |
|------|------|
| **需求** | 3步表单（个人信息→地址→确认），每步有验证，支持前进/后退，最终提交时汇总所有数据 |
| **反直觉约束** | `no_form_lib`（禁止 react-hook-form / formik）+ `validation=runtime`（不允许使用 zod/yup，验证逻辑必须手写）+ `style=plain_css` |
| **多步交叉** | 无表单库 + 无验证库 + 多步导航 = 需要手动实现 step 状态机 + 每步验证逻辑 |
| **预期难点** | 多步表单的 step 管理 + 跨步数据持久化 + 手写验证是复合难度 |
| **功能关键词** | step state machine, per-step validation, email regex, required fields, back navigation preserving data, final summary, submit handler |
| **评分锚点** | 3分 = 三步全通+验证正确+前后导航保留数据+最终汇总；2分 = 能前进但验证不全或后退丢数据；1分 = 只有一步表单；0分 = 缺失 |

### 3.2 Backend 进阶任务（BE-05 ~ BE-08）

#### BE-05：JWTAuthMiddleware（JWT 认证中间件）

| 字段 | 内容 |
|------|------|
| **需求** | FastAPI 中间件：签发 JWT token（login 端点）、验证 JWT（protected 端点）、刷新 token、无效 token 返回 401 |
| **反直觉约束** | `no_jwt_lib`（禁止 PyJWT / python-jose，必须用 hmac + base64 手动实现 JWT 签发/验证）+ `framework=fastapi` + `deps=stdlib_only` |
| **多步交叉** | 无 JWT 库 + 仅标准库 = 需要手动实现 base64url 编码 + HMAC-SHA256 签名 |
| **预期难点** | 模型训练数据中 JWT 实现几乎都用 PyJWT，手动实现需要正确处理 base64url padding 和 HMAC |
| **功能关键词** | base64url encode/decode, hmac sha256, jwt header/payload/signature, expiry check, 401 response, refresh endpoint |
| **评分锚点** | 3分 = 签发+验证+刷新+过期检测全正确；2分 = 能签发但验证有 bug 或无刷新；1分 = 有端点但 JWT 格式错误；0分 = 缺失 |

#### BE-06：WebSocketChat（WebSocket 聊天服务）

| 字段 | 内容 |
|------|------|
| **需求** | FastAPI WebSocket 聊天服务器：多房间、广播消息、用户昵称、在线列表、消息历史（内存） |
| **反直觉约束** | `no_async_lib`（禁止 asyncio.Queue 等异步队列库，广播必须用简单的 set 遍历）+ `deps=fastapi_only`（仅允许 fastapi + uvicorn） |
| **多步交叉** | WebSocket + 多房间 + 广播 = 需要管理 connection registry |
| **预期难点** | WebSocket 的连接生命周期管理（disconnect 清理、broadcast 异常处理）是常见出错点 |
| **功能关键词** | websocket accept/send/close, room dict, connection set, broadcast loop, nickname, online list endpoint, message history list |
| **评分锚点** | 3分 = 多房间+广播+昵称+在线列表+历史全工作；2分 = 单房间能聊但缺多房间或历史；1分 = WebSocket 能连但不能聊；0分 = 缺失 |

#### BE-07：RateLimiter（限流中间件）

| 字段 | 内容 |
|------|------|
| **需求** | Token Bucket 限流中间件：可配置每 IP 的 rate/burst、返回 429 + Retry-After header、支持白名单 IP 跳过限流 |
| **反直觉约束** | `algorithm=token_bucket`（必须实现 Token Bucket 而非简单计数器）+ `storage=in_memory`（禁止 Redis）+ `deps=stdlib_only` |
| **多步交叉** | Token Bucket 算法 + 中间件 + Retry-After 计算 = 需要正确实现令牌补充时间计算 |
| **预期难点** | Token Bucket 的令牌补充逻辑（基于时间差的浮点计算）和线程安全是常见出错点 |
| **功能关键词** | token bucket class, tokens/refill_rate/capacity, per-ip dict, middleware inject, 429 status, Retry-After header, whitelist check |
| **评分锚点** | 3分 = Token Bucket 正确+429+Retry-After+白名单全工作；2分 = 能限流但计算有误或缺 Retry-After；1分 = 中间件存在但不限流；0分 = 缺失 |

#### BE-08：BatchImportAPI（批量导入接口）

| 字段 | 内容 |
|------|------|
| **需求** | CSV 文件上传→逐行解析→验证→入库（内存 dict）→返回成功/失败/跳过计数 + 错误行详情 |
| **反直觉约束** | `no_pandas`（禁止 pandas，必须用 csv 标准库模块）+ `validation=strict`（每行必须验证 email 格式、age 范围 0-150、name 非空）+ `response=streaming`（使用 StreamingResponse 逐行返回处理状态） |
| **多步交叉** | CSV 解析 + 逐行验证 + 流式响应 = 需要 generator-based streaming |
| **预期难点** | StreamingResponse 与 CSV 逐行处理的结合是非标准模式 |
| **功能关键词** | file upload, csv.reader, row validation, email regex, age range check, StreamingResponse, generator yield, error detail list, summary counts |
| **评分锚点** | 3分 = 上传+解析+验证+流式响应+汇总全正确；2分 = 能解析但验证不全或非流式；1分 = 有端点但不能处理 CSV；0分 = 缺失 |

### 3.3 Python 进阶任务（PY-05 ~ PY-08）

#### PY-05：ConcurrentDownloader（并发下载器）

| 字段 | 内容 |
|------|------|
| **需求** | 接收 URL 列表，并发下载所有文件（max_workers 可配置），支持重试、超时、进度回调 |
| **反直觉约束** | `no_requests`（禁止 requests / httpx / aiohttp，必须用 urllib.request）+ `concurrency=threading`（禁止 asyncio，必须用 threading + ThreadPoolExecutor） |
| **多步交叉** | urllib + threading + 重试 + 进度回调 = 需要手动管理线程池和回调机制 |
| **预期难点** | urllib 的 API 比 requests 冗长得多，重试逻辑需要手动实现 |
| **功能关键词** | urllib.request.urlopen, ThreadPoolExecutor, retry with backoff, timeout parameter, progress callback, error collection, result summary |
| **评分锚点** | 3分 = 并发+重试+超时+进度回调全工作；2分 = 能下载但无重试或无并发；1分 = 只有函数签名；0分 = 缺失 |

#### PY-06：DAGScheduler（DAG 任务调度器）

| 字段 | 内容 |
|------|------|
| **需求** | 接收任务依赖图（DAG），拓扑排序确定执行顺序，检测循环依赖，支持并行执行无依赖的任务 |
| **反直觉约束** | `no_networkx`（禁止 networkx / graphlib）+ `output=class`（必须实现为 class 而非函数） |
| **多步交叉** | 手动拓扑排序 + 循环检测 + 并行 = 算法难度较高 |
| **预期难点** | Kahn's algorithm / DFS 拓扑排序 + 环检测是经典算法题，但在"无库"约束下需要完全手写 |
| **功能关键词** | DAG class, add_task/add_dependency, topological_sort, cycle_detection, parallel_groups, execute method, CycleError exception |
| **评分锚点** | 3分 = 拓扑排序+环检测+并行分组全正确；2分 = 排序正确但无环检测或无并行；1分 = 类存在但排序逻辑错误；0分 = 缺失 |

#### PY-07：TemplateEngine（简易模板引擎）

| 字段 | 内容 |
|------|------|
| **需求** | 支持变量替换 `{{var}}`、条件 `{% if cond %}...{% endif %}`、循环 `{% for item in list %}...{% endfor %}`、过滤器 `{{var\|upper}}` |
| **反直觉约束** | `no_jinja`（禁止 jinja2 / mako / 任何模板库）+ `parser=regex`（必须用正则表达式解析模板，禁止 ast 模块）+ `deps=stdlib_only` |
| **多步交叉** | 正则解析 + 条件/循环嵌套 + 过滤器管道 = 需要实现递归或栈式解析 |
| **预期难点** | 嵌套的 if/for 结构用纯正则解析需要递归匹配或分层处理 |
| **功能关键词** | regex pattern for {{var}}, {% if %}, {% for %}, filter pipe, nested blocks, render method, context dict, TemplateSyntaxError |
| **评分锚点** | 3分 = 变量+条件+循环+过滤器+嵌套全正确；2分 = 变量替换正确但条件/循环有bug；1分 = 只有变量替换；0分 = 缺失 |

#### PY-08：ASTCodeChecker（AST 代码检查器）

| 字段 | 内容 |
|------|------|
| **需求** | 接收 Python 源码字符串，使用 ast 模块检查：未使用的 import、未使用的变量、函数过长（>50行）、嵌套过深（>4层） |
| **反直觉约束** | `must_use_ast`（必须使用 ast.NodeVisitor / ast.walk，禁止正则匹配）+ `output=dataclass`（检查结果必须用 dataclass 封装）+ `deps=stdlib_only` |
| **多步交叉** | AST 遍历 + 多种检查规则 + dataclass 输出 = 需要正确实现 visitor pattern |
| **预期难点** | 未使用变量的判定需要区分定义和引用，嵌套深度需要递归计算 |
| **功能关键词** | ast.parse, ast.NodeVisitor, visit_Import/visit_FunctionDef, scope tracking, unused detection, nesting depth counter, dataclass results |
| **评分锚点** | 3分 = 四种检查全正确+dataclass输出；2分 = 2-3种检查正确；1分 = 能 parse 但检查逻辑错误；0分 = 缺失 |

---

## 四、Prompt 变体规范

### 4.1 四组变体的进阶任务模板

每个进阶任务的 Prompt 仍遵循 v2 的四组变体设计，但约束密度更高：

**A (NL) 示例**（FE-05）：
```
Write a React component using TypeScript. Use plain CSS (no Tailwind). 
Do not use any external libraries. Do not use the HTML5 Drag and Drop API.
Implement drag-and-drop reordering using mouse/touch events only.
The component should render a sortable list with visual feedback during drag.
Export as default. Output code only, no explanation.
```

**B (JSON) 示例**（FE-05）：
```json
{
  "language": "TypeScript",
  "framework": "React",
  "style": "plain_css",
  "dependencies": "none",
  "constraints": ["no_html5_drag_api", "mouse_touch_events_only"],
  "output": "export_default",
  "format": "code_only",
  "task": "Draggable sort list with visual feedback during reordering"
}
```

**C (Compact) 示例**（FE-05）：
```
[L]TS [F]React [S]plain_css [D]none [X]no_html5_drag,mouse_touch_only [O]export_default [OUT]code_only
Draggable sort list with visual drag feedback and reorder on drop.
```

**D (Classical) 示例**（FE-05）：
```
[语]TS [架]React [样]原生CSS [依]无 [禁]禁HTML5拖放API,须用鼠标触摸事件 [出]默认导出 [格]纯码
可拖拽排序列表，拖动时有视觉反馈，放下后更新顺序。
```

### 4.2 约束密度对比

| 组 | Pilot 平均约束数 | 进阶任务平均约束数 | 增幅 |
|----|----------------|------------------|------|
| A (NL) | 5-6 | 8-10 | +60% |
| C (Compact) | 5-6 标签 | 8-10 标签 + [X] 字段 | +60% |

---

## 五、评审协议

### 5.1 审查标准

沿用 Pilot 的 R1-R12 协议，但对进阶任务增加以下调整：

| 检查项 | Pilot 标准 | 进阶任务调整 |
|--------|----------|-------------|
| **R6 (no_banned_deps)** | 检查是否导入了禁止的库 | **增加语义级检查**：如 FE-05 需确认无 `dragstart`/`dragover` 等 HTML5 DnD API 调用 |
| **R7 (style_correct)** | 检查 Tailwind/CSS | **增加 CSS modules 检查**：如 FE-06 需确认使用了 `.module.css` 导入模式 |
| **R10 (functionality)** | 3 分制 | **进阶任务使用 5 分制**（0-5），因为功能点更多：0=缺失，1=框架存在，2=核心功能部分工作，3=核心功能全工作但有 bug，4=全功能无 bug，5=全功能+边界处理 |

### 5.2 审查矩阵

| 被审查模型 | 审查模型 | 审查范围 |
|-----------|---------|---------|
| 所有非 Gemini 模型 | Gemini-3.0-Pro | 全部 12 进阶任务 × 4 变体 |
| Gemini-3.0-Pro | GPT-5.4 | 全部 12 进阶任务 × 4 变体 |

---

## 六、模型选择

### 6.1 参与模型

从 Pilot 的 11 个有效模型中选择 **6 个**，覆盖三个层级和克隆/非克隆类别：

| 层级 | 模型 | 选择理由 |
|------|------|---------|
| Pro | **Claude-Opus-4.6** | Pilot 中 全域独立 + 满分，进阶任务中作为能力上限 |
| Pro | **GPT-5.4** | Pilot 中 全域独立 + 满分，与 Opus 形成 Pro 层对照 |
| Mid | **GLM-5.0-Turbo** | Pilot 中 FE 独立 + BE/PY 轻微克隆，中国模型代表 |
| Mid | **Kimi-K2.5** | Pilot 中 FE 独立 + BE/PY 全克隆，测试克隆是否在进阶任务消失 |
| Lite | **DeepSeek-V3.2** | Pilot 中表现最弱但全域独立，进阶任务中预期差异更大 |
| Lite | **Gemini-3.1-flash-lite** | Pilot 中全域独立 + CCR 满分，Lite 层的稳定对照 |

### 6.2 排除模型

| 模型 | 排除理由 |
|------|---------|
| MiniMax-M2.7 | Pilot 中全域全克隆，无法产出有效变体比较数据 |
| GLM-5.0 | 与 GLM-5.0-Turbo 同源，Pilot 中 BE/PY 全克隆 |
| Claude-Haiku-4.5 | BE/PY 全克隆，且 FE-04A 有约束泄露 |
| Gemini-3.0-Flash | Pilot 中表现与 Pro 接近，减少模型数以控制成本 |
| Gemini-3.0-Pro | 仅作为审查模型参与 |

---

## 七、执行标准

### 7.1 生成要求

| 要求 | 规范 |
|------|------|
| **生成次数** | 12 任务 × 4 变体 × 6 模型 = **288 次** |
| **会话隔离** | 每个 (model, task, variant) 必须在**新会话**中执行，禁止同一会话连续生成不同变体 |
| **Prompt 投递** | 每次只投递一个完整 prompt（Header + 需求描述），不做追问或补充 |
| **输出截取** | 只取第一轮回复中的代码块，忽略解释文本 |
| **文件命名** | `v2/generations/{model}/{variant}/{task_id}_{TaskName}.{ext}` |
| **超时处理** | 如果 3 分钟内未返回完整代码，记为文件缺失（Pass@1 = 0） |

### 7.2 审查要求

| 要求 | 规范 |
|------|------|
| **审查时机** | 每个模型生成完毕后立即审查，不等全部模型完成 |
| **去重规则** | 如出现 [REVIEW-RETRY]，以最后一条 RETRY 记录为准 |
| **审查日志** | 追加至同一 `review_log.jsonl`，新增字段 `experiment: "EXP-A"` |
| **汇总报告** | 每模型生成 `review_summary_{model}_EXP_A.md` |

### 7.3 Pass/Fail 判定标准

进阶任务的 Pass@1 判定（CCR ≥ 0.8 且 R10 ≥ 2）：

| 条件 | 判定 |
|------|------|
| CCR = 1.0 且 R10 ≥ 3 | **PASS (Full)** |
| CCR ≥ 0.8 且 R10 ≥ 2 | **PASS (Partial)** |
| CCR < 0.8 或 R10 < 2 | **FAIL** |
| 文件缺失 | **FAIL (Missing)** |

---

## 八、分析计划

### 8.1 主要分析

1. **进阶任务 Pass@1 分布**：期望 Pro 层 70-85%，Mid 层 50-70%，Lite 层 30-50%
2. **C vs A 配对差异**：逐任务、逐模型配对比较，使用 McNemar's test（因为预期不再全 100%）
3. **R10 功能分分布**：期望在 0-5 范围内有正态分布，而非集中在满分
4. **克隆消失验证**：检查 Kimi-K2.5 在 BE-05~08、PY-05~08 上是否仍克隆

### 8.2 预期结果与风险

| 预期 | 依据 | 风险 |
|------|------|------|
| Pass@1 下降到 60-80% | 反直觉约束 + 多步交叉提高难度 | 可能过难导致多数模型 < 30%，失去中间区分度 |
| C ≈ A 在进阶任务上仍然成立 | Compact Header 的信息完整性不变 | 约束密度增加后 Compact 可能遗漏关键信息 |
| BE/PY 克隆消失 | 进阶任务的实现不再有"唯一标准答案" | 可能仍克隆——说明是平台/模型固有行为 |

### 8.3 成功标准

| 标准 | 阈值 |
|------|------|
| Pass@1 整体区间 | 40%-85%（既不全通过也不全失败） |
| 至少 2 个变体对出现显著差异 | McNemar p < 0.05 |
| R10 功能分标准差 | > 1.0（表示有足够的分散度） |

---

## 九、产物清单

| 产物 | 路径 | 说明 |
|------|------|------|
| Prompt 文件 | `v2/prompts/{task_id}_{variant}.txt` | 12 × 4 = 48 个新 prompt |
| 生成代码 | `v2/generations/{model}/{variant}/{task_id}_{name}.{ext}` | 最多 288 个文件 |
| 审查日志 | `v2/audit/review_log.jsonl`（追加） | 字段含 `"experiment": "EXP-A"` |
| 审查汇总 | `v2/audit/review_summary_{model}_EXP_A.md` | 每模型一份 |
| 分析报告 | `v2/analysis/V2_EXP_A_ANALYSIS.md` | 进阶实验专用报告 |

---

*设计时间：2026-03-31 21:42 CST*  
*状态：待用户确认后执行*
