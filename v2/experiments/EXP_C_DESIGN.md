# EXP-C: Multi-Agent Constraint Propagation Experiment Design (v3)

> **设计时间**：2026-04-01 v3（全面修订版）  
> **状态**：Draft — 待确认后执行  
> **定位**：CodePrompt-DSL 论文的第四个实验模块（Pilot → EXP-A → EXP-B → EXP-C）  
> **修正记录**：  
> - v1→v2：模型组合从 3 组扩展到 5 组；加入重复测量；执行方式改为按模型分批  
> - v2→v3：**根据 6 项审查意见全面重构**——任务扩至 12 个（每域 4 个）；模型组合改为 7 组单变量 ablation；编码条件增至 3 组（NL-full / NL-compact / Header）；CSR 改为双层评分（客观二值层 + 主观语义层）；S1 测量增设保真度和可行动性；重复策略改为 appendix robustness check  
> - v3.1：**叙事重定向 + Naturalization Rate**——RQ2 升为 Primary RQ（constraint decay + naturalization 机制）；S1 测量从三指标扩为四指标（增 Representation Form）；新增 H-C8/H-C9 假设；增加 prompt 对齐防污染声明

---

## 0. v3 修改摘要：6 项漏洞逐条回应

| # | 漏洞 | v2 状态 | v3 修改 |
|---|------|---------|---------|
| L1 | 自变量太多、样本太少 | 3 任务 ×5 组合 | **12 任务（FE×4 / BE×4 / PY×4）×7 组合** |
| L2 | 模型组合不够正交 | 5 组混合设计 | **7 组单变量 ablation：每 stage 独立替换** |
| L3 | Header vs NL 不公平 | 2 水平（NL-full / Header） | **3 水平：NL-full / NL-compact / Header** |
| L4 | CSR 打分主观性 | Pass/Partial/Fail 三级 | **双层：L-A 二值客观层 + L-B 主观语义层** |
| L5 | S1 output 测量不够硬 | "是否提及" 单指标 | **三指标：mention rate / fidelity / actionability** |
| L6 | 重复测量策略不平衡 | 核心 pair 重复混在主结果 | **主分析不重复；robustness check 作为 appendix** |

---

## 1. 研究问题

### Primary Research Question

> **RQ-P**: 在多 agent 代码生成链路中，compact structured headers 相对于等长度自然语言约束，是否能维持更高的 constraint survival rate？若不能，其失效是否由跨阶段 naturalization 导致？

这一问题直接锚定 **Header vs NL-compact** 的对照、**CSR** 作为主指标、以及 **naturalization** 作为机制解释。

### Supporting Research Questions

| # | 问题 | 对应假设 | 与 RQ-P 的关系 |
|---|------|---------|---------------|
| RQ-S1 | 在多 Agent 链中，token 累计节省是否因阶段数而被放大？ | H-C1 | 经济性维度——即使 CSR 等效，token 节省仍有独立价值 |
| RQ-S2 | 单变量替换 pipeline 中的某个 stage 时，约束执行的一致性如何变化？哪个 stage 影响最大？ | H-C4 ~ H-C7 | 系统形态维度——约束衰减不仅取决于编码，还取决于 stage 配置 |

### 机制链条（EXP-C 要建立的完整证据链）

```
Header input at S0
  → S1: 约束是否被保留？保留时结构形式是否存活？(mention / fidelity / actionability / naturalization)
  → S2: 约束是否在代码中被实现？(L-A binary compliance)
  → S3: 约束违反是否被审查修复？(repair gain)
  → final CSR
```

如果 Header 在 S1 就被 100% naturalize（转写为自然语言），那到 S2 时模型看到的已经不再是结构化编码——Header 的多 agent 优势在 S1 就消失了。这是 RQ-P 的核心假设。

---

## 2. Agent 管线架构

### 2.1 三阶段管线

```
Stage 1: Architect        Stage 2: Implementer       Stage 3: Auditor
(需求分析 + 技术方案)      (代码实现)                  (审查 + 修复)
         │                        │                         │
    约束层(Header/NL-c/NL-f)  约束层(Header/NL-c/NL-f)   约束层(Header/NL-c/NL-f)
         │                        │                         │
    用户需求               S1 技术方案                 S2 代码产物
                            + 实现指令                  + 审查指令
         │                        │                         │
         ▼                        ▼                         ▼
    技术方案文档               代码文件                   审查报告
   (Markdown,≤2000字)       (.tsx/.py)               + 修复后代码(.tsx/.py)
```

### 2.2 Stage 角色定义

| Stage | 角色 | 输入 | 输出 | 关键约束 |
|-------|------|------|------|---------|
| **S1 Architect** | 需求分析师 | 用户需求 + 约束 | 技术方案（Markdown，≤2000 字） | **不写代码**，只做架构和技术选型 |
| **S2 Implementer** | 开发者 | S1 方案 + 约束 | 代码文件（单文件） | **严格按 S1 方案和约束实现** |
| **S3 Auditor** | 审查员 | S2 代码 + 约束 + 审查清单 | 逐条审查报告 + 修复后完整代码 | **必须逐约束判定 + 输出完整修复代码** |

### 2.3 为什么选三阶段

- S1→S2 存在**信息转换**：约束从结构化格式被 S1 "消化"后嵌入自然语言方案，这是约束衰减最可能发生的节点
- S3 的修复能力检验了**鲁棒型 Auditor 能否挽救前序 stage 的约束损失**
- 三阶段是当前 multi-agent 代码生成的最小完整管线（设计→实现→审查）

---

## 3. 任务设计

### 3.1 设计原则

1. **复杂度高于 Pilot/EXP-A**：避免"全 100%"的天花板效应
2. **每个任务 6 条约束，含 2 条反直觉约束**：反直觉约束是拉开梯度的关键
3. **反直觉约束定义**：要求模型偏离其训练数据中的主流范式（如用 exec() 而非 importlib，用 CSS Modules 而非 Tailwind）
4. **每域 4 个任务**：确保有足够样本将 task idiosyncrasy 与真实效应分离
5. **跨域覆盖**：Frontend × 4 + Backend × 4 + Python × 4 = 12

### 3.2 任务总览

| Task ID | 域 | 名称 | 反直觉约束摘要 |
|---------|---|----|--------------|
| MC-FE-01 | FE | Real-time Collaborative Todo Board | CSS Modules + 手写 HTML5 拖拽 |
| MC-FE-02 | FE | Virtual Scroll Data Grid | 手写虚拟滚动 + CSS Modules |
| MC-FE-03 | FE | Canvas Drawing Whiteboard | 手写 Canvas 2D + useReducer only |
| MC-FE-04 | FE | Multi-Step Form Wizard | 手写验证 + plain CSS |
| MC-BE-01 | BE | Event-Sourced Task Queue | asyncio.Queue + append-only list |
| MC-BE-02 | BE | JWT Auth Middleware | 手写 JWT (hmac+base64) + stdlib only |
| MC-BE-03 | BE | WebSocket Chat Server | 无异步队列库 + fastapi only |
| MC-BE-04 | BE | Rate Limiter Middleware | Token Bucket 手写 + stdlib only |
| MC-PY-01 | PY | Plugin-based Data Pipeline | exec() 加载 + Protocol 接口 |
| MC-PY-02 | PY | DAG Task Scheduler | 手写拓扑排序 + class 输出 |
| MC-PY-03 | PY | Template Engine | 正则解析 + stdlib only |
| MC-PY-04 | PY | AST Code Checker | 必须用 ast + dataclass 输出 |

### 3.3 Frontend 任务详细规格

#### MC-FE-01: Real-time Collaborative Todo Board

**功能需求**：多用户实时协作看板，支持拖拽排序、乐观更新、冲突解决提示。用户可在 Todo/In Progress/Done 三列间拖拽任务卡片。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | TypeScript + React | ❌ | `[L]TS [F]React` | "TS + React" | "Use TypeScript with React framework." |
| C2 | **CSS Modules，禁止 Tailwind** | ✅ | `[Y]CSS_MODULES [!Y]NO_TW` | "CSS Modules only, no Tailwind" | "Use CSS Modules for all styling. Do not use Tailwind CSS or any utility-first CSS framework." |
| C3 | **手写 HTML5 拖拽，禁止所有拖拽库** | ✅ | `[!D]NO_DND_LIB [DRAG]HTML5` | "HTML5 native drag, no dnd libs" | "Implement drag-and-drop using the native HTML5 Drag and Drop API only. Do not use react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library." |
| C4 | useReducer only，禁止状态库 | ❌ | `[STATE]useReducer` | "useReducer only, no state libs" | "Use useReducer for all state management. Do not use Redux, Zustand, Jotai, or other state management libraries." |
| C5 | 单文件 export default | ❌ | `[O]SFC [EXP]DEFAULT` | "Single file, export default" | "Deliver a single .tsx file with export default as the main component." |
| C6 | WebSocket mock 手写，禁止 socket.io | ❌ | `[WS]MOCK [!D]NO_SOCKETIO` | "Hand-written WS mock, no socket.io" | "Simulate real-time sync with a hand-written mock using setTimeout/setInterval. Do not use socket.io or any WebSocket library." |

**功能检查点**（用于 L4 功能分）：
- [ ] 三列看板渲染（Todo / In Progress / Done）
- [ ] 任务卡片 CRUD
- [ ] 列间拖拽移动
- [ ] 列内拖拽排序
- [ ] 乐观更新（UI 先变，后同步）
- [ ] 冲突提示 UI

#### MC-FE-02: Virtual Scroll Data Grid

**功能需求**：支持 10,000 行数据的虚拟滚动表格，固定表头，可排序列，可过滤。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | TypeScript + React | ❌ | `[L]TS [F]React` | "TS + React" | "Use TypeScript with React framework." |
| C2 | **手写虚拟滚动，禁止 windowing 库** | ✅ | `[!D]NO_VIRT_LIB [SCROLL]MANUAL` | "Manual virtual scroll, no react-window" | "Implement virtual scrolling manually. Do not use react-window, react-virtualized, @tanstack/virtual, or any windowing library." |
| C3 | **CSS Modules，禁止 Tailwind 和 inline style** | ✅ | `[Y]CSS_MODULES [!Y]NO_TW_INLINE` | "CSS Modules, no Tailwind/inline" | "Use CSS Modules for all styling. Do not use Tailwind CSS or inline styles." |
| C4 | 无外部依赖 | ❌ | `[D]NO_EXTERNAL` | "No external deps" | "Do not use any external npm packages beyond React and TypeScript." |
| C5 | 单文件 export default | ❌ | `[O]SFC [EXP]DEFAULT` | "Single file, export default" | "Deliver a single .tsx file with export default." |
| C6 | 数据模拟必须内嵌 | ❌ | `[DT]INLINE_MOCK` | "Inline mock data" | "Generate mock data inline in the file. Do not import from external data files." |

**功能检查点**：
- [ ] 10,000 行数据生成
- [ ] 滚动时仅渲染可见行（DOM 节点数受控）
- [ ] 固定表头
- [ ] 列排序（至少 2 列）
- [ ] 列过滤/搜索
- [ ] 滚动流畅无闪烁

#### MC-FE-03: Canvas Drawing Whiteboard

**功能需求**：Canvas 绘画白板，支持画笔/橡皮擦/颜色选择/撤销重做/清除画布。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | TypeScript + React | ❌ | `[L]TS [F]React` | "TS + React" | "Use TypeScript with React framework." |
| C2 | **手写 Canvas 2D，禁止 canvas 库** | ✅ | `[!D]NO_CANVAS_LIB [DRAW]CTX2D` | "Native Canvas 2D, no fabric/konva" | "Use native Canvas 2D context API only. Do not use fabric.js, konva, p5.js, or any canvas/drawing library." |
| C3 | **useReducer only，禁止 useState** | ✅ | `[STATE]useReducer_ONLY` | "useReducer only, no useState" | "Use useReducer for ALL state management. Do not use useState at all." |
| C4 | 无外部依赖 | ❌ | `[D]NO_EXTERNAL` | "No external deps" | "No external npm packages beyond React and TypeScript." |
| C5 | 单文件 export default | ❌ | `[O]SFC [EXP]DEFAULT` | "Single file, export default" | "Deliver a single .tsx file with export default." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] Canvas 画布渲染
- [ ] 画笔绘制（mousedown → mousemove → mouseup）
- [ ] 橡皮擦模式
- [ ] 颜色选择器
- [ ] 撤销/重做
- [ ] 清除画布

#### MC-FE-04: Multi-Step Form Wizard

**功能需求**：3 步表单（个人信息→地址→确认），每步有验证，支持前进/后退，最终提交时汇总所有数据。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | TypeScript + React | ❌ | `[L]TS [F]React` | "TS + React" | "Use TypeScript with React framework." |
| C2 | **手写验证，禁止表单/验证库** | ✅ | `[!D]NO_FORM_LIB [VALID]HANDWRITE` | "Hand-written validation, no formik/zod" | "Implement all form validation by hand. Do not use react-hook-form, formik, zod, yup, or any form/validation library." |
| C3 | **plain CSS，禁止 Tailwind** | ✅ | `[Y]PLAIN_CSS [!Y]NO_TW` | "Plain CSS, no Tailwind" | "Use plain CSS (style tags or CSS files) for styling. Do not use Tailwind CSS." |
| C4 | 无外部依赖 | ❌ | `[D]NO_EXTERNAL` | "No external deps" | "No external npm packages beyond React and TypeScript." |
| C5 | 单文件 export default | ❌ | `[O]SFC [EXP]DEFAULT` | "Single file, export default" | "Deliver a single .tsx file with export default." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] 三步表单渲染（Step 1 / 2 / 3）
- [ ] 每步字段验证（email regex、必填、格式）
- [ ] 前进/后退导航保留数据
- [ ] 最终确认页汇总所有数据
- [ ] 提交 handler
- [ ] 验证错误提示 UI

### 3.4 Backend 任务详细规格

#### MC-BE-01: Event-Sourced Task Queue API

**功能需求**：FastAPI 事件溯源任务队列，支持任务提交、状态查询、自动重试、事件回放。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python + FastAPI | ❌ | `[L]Python [F]FastAPI` | "Python + FastAPI" | "Use Python with FastAPI framework." |
| C2 | 仅 stdlib + fastapi + uvicorn | ❌ | `[D]STDLIB+FASTAPI` | "stdlib + fastapi + uvicorn only" | "Only use Python standard library, fastapi, and uvicorn as dependencies." |
| C3 | **禁止 Celery/RQ，必须用 asyncio.Queue** | ✅ | `[!D]NO_CELERY [Q]ASYNCIO` | "asyncio.Queue only, no Celery/RQ" | "Do not use Celery, RQ, or any task queue library. Implement the queue using asyncio.Queue." |
| C4 | **事件存储 append-only list，禁止 dict 覆盖** | ✅ | `[STORE]APPEND_ONLY` | "Append-only list event store, no dict overwrite" | "The event store must be an append-only list. Never overwrite or delete events. Derive current state by replaying events." |
| C5 | 所有端点幂等 | ❌ | `[API]IDEMPOTENT` | "All endpoints idempotent" | "All API endpoints must be idempotent (same request twice = same result)." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] POST 提交任务（含 idempotency key）
- [ ] GET 查询任务状态
- [ ] 自动重试机制（configurable max retries + backoff）
- [ ] 事件回放端点
- [ ] 内存事件存储（append-only list）
- [ ] asyncio.Queue 驱动的 worker

#### MC-BE-02: JWT Auth Middleware

**功能需求**：FastAPI 中间件：签发 JWT token、验证 JWT、刷新 token、无效 token 返回 401。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python + FastAPI | ❌ | `[L]Python [F]FastAPI` | "Python + FastAPI" | "Use Python with FastAPI framework." |
| C2 | **禁止 PyJWT/python-jose，手写 JWT** | ✅ | `[!D]NO_JWT_LIB [AUTH]MANUAL_JWT` | "Manual JWT via hmac+base64, no PyJWT" | "Do not use PyJWT, python-jose, or any JWT library. Implement JWT signing and verification using hmac and base64 from the standard library." |
| C3 | **仅标准库 + fastapi + uvicorn** | ✅ | `[D]STDLIB+FASTAPI` | "stdlib + fastapi + uvicorn only" | "Only use Python standard library, fastapi, and uvicorn. No other third-party packages." |
| C4 | 单文件 | ❌ | `[O]SINGLE_FILE` | "Single file" | "Deliver everything in a single Python file." |
| C5 | 端点含 login / protected / refresh | ❌ | `[API]LOGIN_PROTECTED_REFRESH` | "Endpoints: login, protected, refresh" | "Provide at minimum: POST /login, GET /protected, POST /refresh endpoints." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] POST /login 签发 JWT
- [ ] GET /protected 验证 JWT + 返回 401
- [ ] POST /refresh 刷新 token
- [ ] JWT 使用 HMAC-SHA256 签名
- [ ] base64url 编码正确
- [ ] 过期检测

#### MC-BE-03: WebSocket Chat Server

**功能需求**：FastAPI WebSocket 聊天服务器：多房间、广播消息、用户昵称、在线列表、消息历史（内存）。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python + FastAPI | ❌ | `[L]Python [F]FastAPI` | "Python + FastAPI" | "Use Python with FastAPI framework." |
| C2 | **禁止异步队列库，广播用 set 遍历** | ✅ | `[!D]NO_ASYNC_Q [BCAST]SET_ITER` | "No asyncio.Queue for broadcast, use set iteration" | "Do not use asyncio.Queue or any async queue for broadcasting. Broadcast by iterating a set of active connections." |
| C3 | **仅 fastapi + uvicorn** | ✅ | `[D]FASTAPI_ONLY` | "fastapi + uvicorn only" | "Only use fastapi and uvicorn. No other third-party packages." |
| C4 | 单文件 | ❌ | `[O]SINGLE_FILE` | "Single file" | "Deliver everything in a single Python file." |
| C5 | 消息历史用 list，≤100 条 | ❌ | `[HIST]LIST_100` | "In-memory list, max 100 msgs per room" | "Store message history in a list per room, capped at 100 messages." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] WebSocket 连接 accept/send/close
- [ ] 多房间路由
- [ ] 广播消息给同房间所有用户
- [ ] 昵称设置
- [ ] 在线列表端点
- [ ] 消息历史

#### MC-BE-04: Rate Limiter Middleware

**功能需求**：Token Bucket 限流中间件：可配置每 IP 的 rate/burst、返回 429 + Retry-After header、支持白名单 IP。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python + FastAPI | ❌ | `[L]Python [F]FastAPI` | "Python + FastAPI" | "Use Python with FastAPI framework." |
| C2 | **必须 Token Bucket 算法，禁止简单计数器** | ✅ | `[ALGO]TOKEN_BUCKET [!A]NO_COUNTER` | "Token Bucket required, no simple counter" | "Implement rate limiting using the Token Bucket algorithm. Do not use simple counter-based or fixed window approaches." |
| C3 | **仅标准库 + fastapi，禁止 Redis** | ✅ | `[D]STDLIB+FASTAPI [!D]NO_REDIS` | "stdlib + fastapi only, no Redis" | "Only use Python standard library and fastapi. Do not use Redis, memcached, or any external storage." |
| C4 | 单文件 | ❌ | `[O]SINGLE_FILE` | "Single file" | "Deliver everything in a single Python file." |
| C5 | 429 + Retry-After + 白名单 | ❌ | `[RESP]429_RETRY_AFTER [WL]IP` | "429 with Retry-After, IP whitelist" | "Return HTTP 429 with Retry-After header when rate exceeded. Support an IP whitelist that bypasses rate limiting." |
| C6 | 纯代码输出 | ❌ | `[OUT]CODE_ONLY` | "Code only" | "Output code only, no explanation text." |

**功能检查点**：
- [ ] Token Bucket class（tokens / refill_rate / capacity）
- [ ] per-IP bucket 字典
- [ ] FastAPI Middleware 注入
- [ ] 429 状态码
- [ ] Retry-After header 计算
- [ ] 白名单 IP 放行

### 3.5 Python 任务详细规格

#### MC-PY-01: Plugin-based Data Pipeline

**功能需求**：支持运行时加载插件的 ETL pipeline，插件实现统一 transform 接口，pipeline 支持条件分支和错误隔离。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python 3.10+，仅标准库 | ❌ | `[L]PY310 [D]STDLIB_ONLY` | "Python 3.10+, stdlib only" | "Python 3.10 or later, standard library only." |
| C2 | **禁止 importlib，必须用 exec() 加载插件** | ✅ | `[!D]NO_IMPORTLIB [PLUGIN]EXEC` | "exec() for plugin loading, no importlib" | "Do not use importlib for plugin loading. Load plugins by reading the file and using exec()." |
| C3 | **禁止 ABC，接口用 Protocol** | ✅ | `[!D]NO_ABC [IFACE]PROTOCOL` | "Protocol for interfaces, no ABC" | "Do not use ABC (Abstract Base Class). Define interfaces using typing.Protocol." |
| C4 | 完整类型标注 | ❌ | `[TYPE]FULL_HINTS` | "Full type annotations" | "Full type annotations on all public methods and class attributes." |
| C5 | 错误隔离 | ❌ | `[ERR]ISOLATE` | "Plugin errors isolated" | "Plugin errors must be isolated. One plugin failure must not crash the pipeline." |
| C6 | 单文件 class 输出 | ❌ | `[O]CLASS [FILE]SINGLE` | "Single file, class output" | "Deliver a single Python file with a Pipeline class as main output." |

**功能检查点**：
- [ ] Pipeline class 接受插件列表
- [ ] exec() 从文件路径加载插件
- [ ] Protocol 定义的 transform 接口
- [ ] pipeline.run(data) 按顺序执行
- [ ] 条件分支（某些插件仅条件满足时执行）
- [ ] 错误隔离 + 日志

#### MC-PY-02: DAG Task Scheduler

**功能需求**：接收任务依赖图（DAG），拓扑排序确定执行顺序，检测循环依赖，支持并行执行无依赖的任务。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python 3.10+，仅标准库 | ❌ | `[L]PY310 [D]STDLIB_ONLY` | "Python 3.10+, stdlib only" | "Python 3.10 or later, standard library only." |
| C2 | **禁止 networkx/graphlib** | ✅ | `[!D]NO_GRAPH_LIB` | "No networkx/graphlib" | "Do not use networkx, graphlib, or any graph library. Implement topological sort from scratch." |
| C3 | **输出必须是 class** | ✅ | `[O]CLASS` | "Output as class" | "The main output must be a class (not standalone functions)." |
| C4 | 完整类型标注 | ❌ | `[TYPE]FULL_HINTS` | "Full type annotations" | "Full type annotations on all public methods." |
| C5 | 循环检测抛自定义异常 | ❌ | `[ERR]CYCLE_EXC` | "CycleError on cycles" | "Raise a custom CycleError exception when a cycle is detected." |
| C6 | 单文件 | ❌ | `[FILE]SINGLE` | "Single file" | "Deliver a single Python file." |

**功能检查点**：
- [ ] DAGScheduler class
- [ ] add_task / add_dependency 方法
- [ ] topological_sort 正确
- [ ] 循环检测 + CycleError
- [ ] parallel_groups（同层可并行）
- [ ] execute 方法

#### MC-PY-03: Template Engine

**功能需求**：支持 `{{var}}`、`{% if cond %}...{% endif %}`、`{% for item in list %}...{% endfor %}`、`{{var|upper}}`。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python 3.10+，仅标准库 | ❌ | `[L]PY310 [D]STDLIB_ONLY` | "Python 3.10+, stdlib only" | "Python 3.10 or later, standard library only." |
| C2 | **禁止 jinja2/mako，必须正则解析** | ✅ | `[!D]NO_TMPL_LIB [PARSE]REGEX` | "Regex parsing, no jinja2/mako" | "Do not use jinja2, mako, or any template library. Parse templates using regular expressions." |
| C3 | **禁止 ast 模块** | ✅ | `[!D]NO_AST` | "No ast module" | "Do not use the ast module for expression evaluation." |
| C4 | 完整类型标注 | ❌ | `[TYPE]FULL_HINTS` | "Full type annotations" | "Full type annotations on all public methods." |
| C5 | 模板错误抛 TemplateSyntaxError | ❌ | `[ERR]SYNTAX_EXC` | "TemplateSyntaxError on errors" | "Raise a custom TemplateSyntaxError for malformed templates." |
| C6 | 单文件 class 输出 | ❌ | `[O]CLASS [FILE]SINGLE` | "Single file, class output" | "Deliver a single Python file with a TemplateEngine class." |

**功能检查点**：
- [ ] `{{var}}` 变量替换
- [ ] `{% if %}...{% endif %}` 条件
- [ ] `{% for %}...{% endfor %}` 循环
- [ ] `{{var|filter}}` 过滤器管道
- [ ] 嵌套结构正确处理
- [ ] TemplateSyntaxError

#### MC-PY-04: AST Code Checker

**功能需求**：接收 Python 源码字符串，检查：未使用的 import、未使用的变量、函数过长（>50 行）、嵌套过深（>4 层）。

**约束集**：

| # | 约束 | 反直觉？ | Header Token | NL-compact | NL-full |
|---|------|---------|-------------|-----------|---------|
| C1 | Python 3.10+，仅标准库 | ❌ | `[L]PY310 [D]STDLIB_ONLY` | "Python 3.10+, stdlib only" | "Python 3.10 or later, standard library only." |
| C2 | **必须使用 ast.NodeVisitor，禁止正则** | ✅ | `[MUST]AST_VISITOR [!D]NO_REGEX` | "ast.NodeVisitor required, no regex" | "Must use ast.NodeVisitor or ast.walk for code analysis. Do not use regular expressions for code pattern matching." |
| C3 | **输出必须用 dataclass** | ✅ | `[O]DATACLASS` | "Results as dataclass" | "Wrap all check results in dataclass instances." |
| C4 | 完整类型标注 | ❌ | `[TYPE]FULL_HINTS` | "Full type annotations" | "Full type annotations on all public methods." |
| C5 | 四种检查全部实现 | ❌ | `[CHECK]IMPORT+VAR+LEN+NEST` | "Check: unused import/var, long func, deep nest" | "Implement all four checks: unused imports, unused variables, function length > 50 lines, nesting depth > 4." |
| C6 | 单文件 class 输出 | ❌ | `[O]CLASS [FILE]SINGLE` | "Single file, class output" | "Deliver a single Python file with a CodeChecker class." |

**功能检查点**：
- [ ] ast.parse 正确解析输入
- [ ] 未使用 import 检测
- [ ] 未使用变量检测
- [ ] 函数长度检测（>50 行）
- [ ] 嵌套深度检测（>4 层）
- [ ] dataclass 封装结果

---

## 4. 实验变量设计

### 4.1 自变量 1：约束编码方式（3 水平）— 修复 L3

| 条件代号 | 约束表达方式 | 字数量级 | 设计意图 |
|----------|------------|---------|---------|
| **NL-f** (NL-full) | 完整自然语言重述全部 6 条约束 | ~120 词 | 信息充分但冗长 |
| **NL-c** (NL-compact) | 紧凑自然语言重述全部 6 条约束 | ~50 词 | **控制组**——与 Header 等长度，证明差异来自形式而非长度 |
| **H** (Header) | Compact header 一行 + 简短 NL 任务描述 | ~50 词 | 结构化编码 |

**关键设计**：NL-c 与 H 在 token 量级上**刻意对齐**，从而隔离：
- NL-f vs NL-c = **冗余度效应**（长 vs 短，同为自然语言）
- NL-c vs H = **形式效应**（同长度，自然语言 vs 结构化）
- NL-f vs H = 混合效应（不可单独归因）

**三组编码的 token 量级对齐示例**（以 MC-FE-01 的约束部分为例）：

```
NL-full (~120 words):
1. Use TypeScript with React framework.
2. Use CSS Modules for all styling. Do not use Tailwind CSS or any utility-first CSS framework.
3. Implement drag-and-drop using the native HTML5 Drag and Drop API only. Do not use react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library.
4. Use useReducer for all state management. Do not use Redux, Zustand, Jotai, or other state management libraries.
5. Deliver a single .tsx file with export default as the main component.
6. Simulate real-time sync with a hand-written mock using setTimeout/setInterval. Do not use socket.io or any WebSocket library.

NL-compact (~50 words):
TS + React. CSS Modules only, no Tailwind. HTML5 native drag, no dnd libs. useReducer only, no state libs. Single file, export default. Hand-written WS mock, no socket.io.

Header (~40 tokens):
[L]TS [F]React [Y]CSS_MODULES [!Y]NO_TW [!D]NO_DND_LIB [DRAG]HTML5 [STATE]useReducer [O]SFC [EXP]DEFAULT [WS]MOCK [!D]NO_SOCKETIO
```

### 4.2 自变量 2：模型行为类型组合（7 水平 — 单变量 ablation）— 修复 L2

采用**单变量 ablation**：以 RRR 为基线，每次只替换一个 stage，使得每个 stage 的影响可独立归因。

| 代号 | S1 Architect | S2 Implementer | S3 Auditor | 变化位 | 设计意图 |
|------|-------------|----------------|-----------|-------|---------|
| **RRR** | Opus (R) | Opus (R) | Opus (R) | — | **全鲁棒基线**：约束传递上限 |
| **CRR** | Kimi (C) | Opus (R) | Opus (R) | S1 → C | S1 换收敛型：方案文档是否"吸收"约束 |
| **SRR** | DeepSeek (S) | Opus (R) | Opus (R) | S1 → S | S1 换敏感型：方案生成是否中断/截断 |
| **RCR** | Opus (R) | Kimi (C) | Opus (R) | S2 → C | S2 换收敛型：实现是否偏离 S1 方案 |
| **RSR** | Opus (R) | DeepSeek (S) | Opus (R) | S2 → S | S2 换敏感型：代码生成是否中断 |
| **RRC** | Opus (R) | Opus (R) | Kimi (C) | S3 → C | S3 换收敛型：审查是否放过约束违反 |
| **RRS** | Opus (R) | Opus (R) | DeepSeek (S) | S3 → S | S3 换敏感型：审查是否格式异常 |

**模型代号**：R = 指令鲁棒型（Robust, Opus）、C = 内容收敛型（Convergent, Kimi）、S = 格式敏感型（Sensitive, DeepSeek）

**可归因性分析**：
```
S1 影响 = (CRR − RRR) 和 (SRR − RRR)
S2 影响 = (RCR − RRR) 和 (RSR − RRR)
S3 影响 = (RRC − RRR) 和 (RRS − RRR)
```

每对差值**只改动一个变量**，因此可以干净归因。

### 4.3 完整实验矩阵

```
12 任务 × 3 编码 × 7 组合 = 252 个管线
每管线 3 stages = 756 次模型调用
```

### 4.4 假设清单

| 假设 | 预期 | 检验方法 |
|------|------|---------|
| **H-C1**: H 条件 token < NL-f 条件 token，且与 NL-c 相当 | 约束部分节省 ×3 放大（仅 NL-f vs H） | token 统计 |
| **H-C2**: NL-c vs H 的最终 CSR 差异揭示"形式效应" | H ≥ NL-c（结构化编码不劣于等长度 NL） | CSR 对比 |
| **H-C3**: NL-f vs NL-c 的 CSR 差异揭示"冗余度效应" | NL-f ≈ NL-c 或 NL-f < NL-c（冗长可能引入噪声） | CSR 对比 |
| **H-C4**: S2 替换（RCR/RSR）对 CSR 影响最大 | S2 是代码实现层，约束执行的主战场 | 差值分析 |
| **H-C5**: S1 替换（CRR/SRR）影响通过 S1→S2 衰减间接传播 | CRR 的 S1 output 遗漏约束 → S2 也遗漏 | 衰减追踪 |
| **H-C6**: S3 替换（RRC/RRS）影响最小 | Auditor 有约束兜底，但非生成核心 | 差值分析 |
| **H-C7**: 反直觉约束的衰减率高于常规约束 | 2 条反直觉约束的平均 CSR < 4 条常规约束 | 分组 CSR |
| **H-C8** *(新增)*: Header 条件下 S1 output 的 Naturalization Rate 接近 100% | S1（Architect）会将 header tokens 翻译为自然语言方案文档，结构化形式在 S1→S2 handoff 时几乎完全消失 | Naturalization Rate 统计 |
| **H-C9** *(新增)*: Naturalization Rate 与 S2 约束违反率正相关 | 约束被 naturalize 得越彻底，S2 违反概率越高（结构化残留越多，S2 遵循越好） | NatRate vs CSR-obj 相关分析 |

---

## 5. 测量指标体系

### 5.1 L-A — 约束客观二值层 (Objective Binary Check)  — 修复 L4

对最终输出（S3 产物）的**每条约束**做二值判定：

| 评级 | 定义 | 分值 | 判定规则 |
|------|------|------|---------|
| **Satisfied** | 约束被遵循 | 1 | 基于**可程序化/规则化**的客观检查 |
| **Not Satisfied** | 约束被违反 | 0 | 同上 |

**每条约束的客观判定规则**（示例，所有 12 个任务的完整规则表见 Appendix A）：

| 任务 | 约束 | Satisfied 规则 | Not Satisfied 规则 |
|------|------|-------------|------------------|
| MC-FE-01 | C2: CSS Modules | 文件中包含 `.module.css` 引用或 `styles.xxx` 语法；不包含 `className="..."` utility classes 或 `tailwind` import | 包含 tailwind import 或 utility class pattern |
| MC-FE-01 | C3: HTML5 Drag | 包含 `onDragStart/onDragOver/onDrop` handler；不包含 `react-dnd`/`dnd-kit` 等 import | 包含任何 dnd 库 import |
| MC-BE-01 | C3: asyncio.Queue | 包含 `asyncio.Queue()` 实例化；不包含 `celery`/`rq` import | 包含 celery/rq 或无 asyncio.Queue |
| MC-BE-01 | C4: append-only | 事件存储使用 `.append()` 且无 `del`/`pop`/`[i]=` 修改操作 | 存在覆盖/删除/修改事件的代码 |
| MC-PY-01 | C2: exec() load | 包含 `exec(` 调用用于加载插件；不包含 `importlib` import | 使用 importlib 或其他加载方式 |
| MC-PY-01 | C3: Protocol | 包含 `Protocol` 定义接口；不包含 `ABC`/`abstractmethod` | 使用 ABC |

> **注意**：L-A 层的核心价值是 **reviewer 可复现**——给定源代码和规则表，任何人用 grep/AST 工具能得到相同结果。

**L-A 汇总指标**：
- **CSR-obj** = Σ(Satisfied) / 6 per pipeline
- **CSR-obj-normal** = 4 条常规约束的平均
- **CSR-obj-counter** = 2 条反直觉约束的平均

### 5.2 L-B — 约束主观语义层 (Semantic Adherence)  — 修复 L4

在 L-A 之外，单独加一个主观评分维度，针对**整体语义忠实度**：

| 维度 | 定义 | 量表 |
|------|------|------|
| **Semantic Adherence** | 产物是否忠实于约束的**意图**，而不仅是字面规则 | 1-5 Likert |

量表锚定：
- 5 = 所有约束意图完全实现，无语义偏差
- 4 = 轻微偏差（如 CSS Modules 为主但混入少量 inline style）
- 3 = 部分约束意图被曲解（如"append-only"存储但有条件删除）
- 2 = 多条约束意图被忽略或替代
- 1 = 产物与约束集几乎无关

> **L-A vs L-B 的关系**：L-A 是硬指标（binary, reproducible），L-B 是补充（ordinal, subjective）。论文主结果用 L-A，L-B 作为 robustness check 放在 appendix。

### 5.3 L2 — 约束衰减追踪 (Constraint Decay Trace)  — 修复 L5

在管线的**每个阶段**测量约束传播状态。S1 层使用三指标体系：

#### 5.3.1 S1 Output 四指标 — 修复 L5 + Naturalization

| 指标 | 定义 | 量表 | 示例 |
|------|------|------|------|
| **Mention Rate** | 约束是否被 S1 技术方案明确提及 | binary (1/0) | "使用 CSS Modules" → 1；完全未提及 → 0 |
| **Fidelity** | 提及时是否**保真**于原始约束的含义 | 3 级：Exact / Shifted / Distorted | "CSS Modules preferred" = Shifted（原约束是 mandatory）；"CSS Modules, 禁止 Tailwind" = Exact |
| **Actionability** | S2 能否直接按 S1 的表述实现 | binary (1/0) | "建议使用原生拖拽" = 0（S2 可能选择 dnd-kit）；"必须使用 HTML5 onDragStart/onDragOver/onDrop" = 1 |
| **Representation Form** *(新增)* | 约束在 S1 输出中的表达形式 | 3 类：Structured / Naturalized / Omitted | 见下文 |

#### 5.3.2 Naturalization Rate — 核心机制指标 *(新增)*

**为什么需要这个指标**：

CSR 告诉我们"约束活没活下来"。但 CSR 无法回答一个更深的问题：**活下来的约束还保不保持结构形式？** 如果 Header 输入到 S1 后，S1 把所有 header token 翻译成自然语言句子，那 S2 看到的已经不再是结构化编码——Header 的形式优势在 S1 就被"翻译掉"了。

**标注分类**（对每条被 S1 保留的约束）：

| 分类 | 定义 | 示例 |
|------|------|------|
| **Structured** | 仍保持 header-like / key-value / 明确枚举形式 | S1 写出 "`[Y]CSS_MODULES`" 或 "Constraint: CSS Modules = required, Tailwind = forbidden" |
| **Naturalized** | 转写为自然语言句子 | S1 写出 "我们将使用 CSS Modules 来管理样式，避免使用 Tailwind" |
| **Omitted** | 未出现 | 完全未提及（已被 Mention Rate 捕获，不进入 NatRate 分母） |

**Naturalization Rate 定义**：

```
NatRate = Naturalized / (Structured + Naturalized)
```

即：**在被保留下来的约束中，有多少已经丢失结构形式**。

- Omitted 不进入分母（因为遗漏已被 Mention Rate 捕获）
- NatRate = 1.0 → S1 完全自然语言化了所有保留约束
- NatRate = 0.0 → S1 保持了全部结构化形式（极不可能，但理论存在）

**论文中的位置**：NatRate 是 RQ-P 的核心证据。如果 Header 条件下 NatRate ≈ 1.0（H-C8），则 Header 的结构化优势在 S1 就被消解——这解释了为什么 Header 在多 agent 链中可能不再优于 NL-compact。

**跨编码对照**：
- Header 条件：NatRate 有意义（测量结构化→自然语言的转写程度）
- NL-compact 条件：NatRate 定义为 1.0（输入本就是自然语言，无"结构化→自然语言"的转变可能）
- NL-full 条件：NatRate 定义为 1.0（同理）

#### 5.3.3 衰减定义修正

```
S1 衰减 = mention × fidelity × actionability × representation form 的综合判定
  - Mention=1, Fidelity=Exact, Actionability=1, Form=Structured → 无衰减（约束完整且保持结构）
  - Mention=1, Fidelity=Exact, Actionability=1, Form=Naturalized → 形式衰减（约束完整但结构消失）
  - Mention=1, Fidelity=Shifted, Actionability=1 → 语义衰减（约束被软化）
  - Mention=1, Fidelity=Exact, Actionability=0 → 行动衰减（约束正确但太模糊）
  - Mention=0 → 完全衰减
```

#### 5.3.4 S2/S3 Output 测量

| 阶段 | 对象 | 测量方式 |
|------|------|---------|
| **S0** | 输入 prompt | 基线 = 6/6（所有约束都在 prompt 中） |
| **S1** | 技术方案 | Mention Rate + Fidelity + Actionability + Representation Form（四指标） |
| **S2** | 代码 | L-A 二值判定（Satisfied/Not Satisfied） |
| **S3** | 修复后代码 | L-A 二值判定 |

#### 5.3.5 衰减曲线输出格式

```
MC-FE-01 | Header | RCR | Run 1:
  C1 (TS+React):        S0=✓  S1=[M=1,F=E,A=1,R=Nat]  S2=Sat   S3=Sat   → 形式衰减但S2仍遵循
  C2 (CSS Modules):     S0=✓  S1=[M=1,F=S,A=1,R=Nat]  S2=NotS  S3=Sat   → 语义+形式衰减→S2违反→S3修复
  C3 (HTML5 Drag):      S0=✓  S1=[M=1,F=E,A=0,R=Nat]  S2=NotS  S3=NotS  → 行动衰减→S2违反→S3未修复
  C4 (useReducer):      S0=✓  S1=[M=1,F=E,A=1,R=Str]  S2=Sat   S3=Sat   → 无衰减（罕见的结构保留）
  C5 (SFC/default):     S0=✓  S1=[M=1,F=E,A=1,R=Nat]  S2=Sat   S3=Sat   → 形式衰减但S2仍遵循
  C6 (WS mock):         S0=✓  S1=[M=0,F=-,A=-,R=Om]   S2=NotS  S3=NotS  → 完全衰减
  NatRate = 4 Nat / (1 Str + 4 Nat) = 0.80
```

### 5.4 L3 — Token 经济性

| 测量项 | 方法 |
|--------|------|
| 每 stage prompt 总 token | 字数估算（英文 ×1.3）或平台显示 |
| 约束部分 token 占比 | 手工标注边界 |
| 三阶段累计约束 token | 求和 |
| **Token 放大系数** | = 多 agent 约束 token 总量 / 单次约束 token |
| **NL-f vs H 节省率** | = (NL-f_total − H_total) / NL-f_total |
| **NL-c vs H 差值** | 应≈0（验证 token 量级对齐） |

### 5.5 L4 — 功能完整性（0-5 分）

| 分 | 标准 |
|----|------|
| 5 | 全部功能检查点通过 + CSR-obj = 1.0 + 代码可运行 |
| 4 | 全部功能检查点 + CSR-obj ≥ 5/6 |
| 3 | ≥75% 功能检查点 + CSR-obj ≥ 4/6 |
| 2 | 50-74% 功能检查点 或 CSR-obj ≤ 3/6 |
| 1 | 框架存在但功能严重缺失 |
| 0 | 文件缺失/空/不相关 |

### 5.6 L5 — Stage 影响归因分析

基于单变量 ablation 的差值分析：

| 分析 | 公式 | 解读 |
|------|------|------|
| S1 影响（C 类型） | ΔCSR_S1C = CSR(CRR) − CSR(RRR) | 负值 = 收敛型 Architect 导致衰减 |
| S1 影响（S 类型） | ΔCSR_S1S = CSR(SRR) − CSR(RRR) | 负值 = 敏感型 Architect 导致衰减 |
| S2 影响（C 类型） | ΔCSR_S2C = CSR(RCR) − CSR(RRR) | 负值 = 收敛型 Implementer 偏离方案 |
| S2 影响（S 类型） | ΔCSR_S2S = CSR(RSR) − CSR(RRR) | 负值 = 敏感型 Implementer 生成中断 |
| S3 影响（C 类型） | ΔCSR_S3C = CSR(RRC) − CSR(RRR) | 负值 = 收敛型 Auditor 放过违反 |
| S3 影响（S 类型） | ΔCSR_S3S = CSR(RRS) − CSR(RRR) | 负值 = 敏感型 Auditor 审查异常 |

**交叉分析**：
- 哪个 stage 的 |ΔCSR| 最大 → 最关键的 stage
- C 类型 vs S 类型在同一 stage 的 |ΔCSR| 差异 → 行为模式对 stage 的交互效应

---

## 6. 重复测量与统计策略  — 修复 L6

### 6.1 主分析：全样本，不重复

**12 × 3 × 7 = 252 个管线**，每个管线执行 1 次。

理由：
- 12 个任务 × 3 个域已提供足够的"任务内重复"来分离 task idiosyncrasy
- 756 次模型调用的成本已经很高
- 主分析聚焦于**效应方向**和**效应大小**，而非 p 值

### 6.2 Appendix：Robustness Check（稳定性检验）

对**核心对比 pair**做 2 次独立重复：

| Pair | 第一次 | 第二次 | 目的 |
|------|--------|--------|------|
| RRR × H | 12 管线 | 12 管线 | 全鲁棒基线稳定性 |
| RCR × H | 12 管线 | 12 管线 | 最关键 ablation 对稳定性 |

额外成本：24 × 2 = 48 管线 × 3 stages = 144 次调用。

### 6.3 声明模板

论文中显式声明：

> **Primary analysis** is conducted on the full 252-pipeline matrix without replication. Each task is treated as an independent observation within its domain, with 4 tasks per domain providing within-domain variance estimates.  
>  
> **Stability check** (Appendix X): We independently replicate the RRR×Header and RCR×Header conditions (the core baseline and its most critical ablation) to assess result stability. This check is reported separately and does not enter the primary analysis.

---

## 7. Prompt 模板

### 7.1 三种编码条件的 Prompt 结构

**所有三种条件共享**：
- 相同的 Role instruction（"You are a software architect / developer / reviewer"）
- 相同的 User Requirement 功能描述
- 相同的 Output format instructions
- 相同的 Include 列表（设计文档应包含的章节）

**唯一不同**：约束表达方式（在 prompt 中的位置和形式）

> ⚠️ **Prompt 对齐原则（Naturalization 防污染）**
>
> 既然 Naturalization Rate 是 RQ-P 的核心机制指标，S1 的 prompt 必须对所有编码条件**严格对齐**，不能暗中鼓励某一组"转写成自然语言"或"保持结构化形式"。
>
> **禁止出现的偏差**：
> - ❌ Header 条件写 "请先解释这些字段的含义"（暗示 naturalize）
> - ❌ NL 条件写 "请给出结构化实现方案"（暗示 structure）
> - ❌ 任何条件写 "在方案中保留约束的原始格式"（直接干预 representation form）
>
> **必须遵守**：
> - ✅ 三种条件的 instruction 文本**逐字相同**（除约束表达段落外）
> - ✅ 约束段落的引导语使用中性措辞："Given the engineering constraints above/below"
> - ✅ Include 列表中的 "Constraint acknowledgment" 只要求 "state how the design addresses each constraint"——不规定表达形式
>
> 这确保 Naturalization Rate 的测量结果反映的是**模型自发行为**，而不是 prompt 诱导的结果。

#### S1 Architect — Header 条件（以 MC-FE-01 为例）

```
[L]TS [F]React [Y]CSS_MODULES [!Y]NO_TW [!D]NO_DND_LIB [DRAG]HTML5 [STATE]useReducer [O]SFC [EXP]DEFAULT [WS]MOCK [!D]NO_SOCKETIO

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. **Constraint acknowledgment section**: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints.
```

#### S1 Architect — NL-compact 条件

```
You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
TS + React. CSS Modules only, no Tailwind. HTML5 native drag, no dnd libs. useReducer only, no state libs. Single file, export default. Hand-written WS mock, no socket.io.

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. **Constraint acknowledgment section**: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints.
```

#### S1 Architect — NL-full 条件

```
You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use TypeScript with React framework.
2. Use CSS Modules for all styling. Do not use Tailwind CSS or any utility-first CSS framework.
3. Implement drag-and-drop using the native HTML5 Drag and Drop API only. Do not use react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library.
4. Use useReducer for all state management. Do not use Redux, Zustand, Jotai, or other state management libraries.
5. Deliver a single .tsx file with export default as the main component.
6. Simulate real-time sync with a hand-written mock using setTimeout/setInterval. Do not use socket.io or any WebSocket library.

Include:
1. Component architecture (what components, their responsibilities)
2. Data model (TypeScript interfaces)
3. State management approach
4. Key implementation approaches for constrained areas
5. **Constraint acknowledgment section**: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) with drag-and-drop. Support optimistic updates and conflict resolution hints.
```

### 7.2 S2/S3 模板结构（同上，仅替换 Role + Input）

S2/S3 的三种编码条件遵循相同模式，此处省略。完整 prompt 集将在执行指令文档中给出。

---

## 8. 模型调用统计

### 8.1 各模型在各 stage 的调用次数

| 模型 | 作为 S1 | 作为 S2 | 作为 S3 | 总计 |
|------|--------|--------|--------|------|
| **Opus (R)** | RRR+RCR+RSR+RRC+RRS = 5组 × 12任务 × 3编码 = **180** | RRR+CRR+SRR+RRC+RRS = 5组 × 12 × 3 = **180** | RRR+CRR+SRR+RCR+RSR = 5组 × 12 × 3 = **180** | **540** |
| **Kimi (C)** | CRR = 1组 × 12 × 3 = **36** | RCR = 1组 × 12 × 3 = **36** | RRC = 1组 × 12 × 3 = **36** | **108** |
| **DeepSeek (S)** | SRR = 1组 × 12 × 3 = **36** | RSR = 1组 × 12 × 3 = **36** | RRS = 1组 × 12 × 3 = **36** | **108** |
| **总计** | **252** | **252** | **252** | **756** |

加 Robustness Check：+48 × 3 = +144 → **总计 900 次**

### 8.2 执行顺序（分 Stage 滚动批次）

为最大化并行度和减少模型切换，按 stage 滚动：

```
Phase 1: 所有 S1（252 次调用）
  批次 1a: Opus 做 S1（180 个会话）
  批次 1b: Kimi 做 S1（36 个会话）  
  批次 1c: DeepSeek 做 S1（36 个会话）
  → 完成后：252 份技术方案文档
  → 中间处理：把 S1 输出嵌入 S2 prompt

Phase 2: 所有 S2（252 次调用）
  批次 2a: Opus 做 S2（180 个会话）
  批次 2b: Kimi 做 S2（36 个会话）
  批次 2c: DeepSeek 做 S2（36 个会话）
  → 完成后：252 份代码文件
  → 中间处理：把 S2 输出嵌入 S3 prompt

Phase 3: 所有 S3（252 次调用）
  批次 3a: Opus 做 S3（180 个会话）
  批次 3b: Kimi 做 S3（36 个会话）
  批次 3c: DeepSeek 做 S3（36 个会话）
  → 完成后：252 份审查报告 + 修复代码

Phase 4: Robustness Check（144 次调用）
  仅 Opus，RRR×H 和 RCR×H 的 12×2 管线重复
```

---

## 9. 文件组织

```
v2/experiments/EXP_C/
├── EXP_C_DESIGN.md                    ← 本文件
├── prompts/
│   ├── MC-FE-01/
│   │   ├── S1_header.md
│   │   ├── S1_nl_compact.md
│   │   ├── S1_nl_full.md
│   │   ├── S2_header_template.md      ← 含 {S1_OUTPUT} 占位符
│   │   ├── S2_nl_compact_template.md
│   │   ├── S2_nl_full_template.md
│   │   ├── S3_header_template.md      ← 含 {S2_OUTPUT} 占位符
│   │   ├── S3_nl_compact_template.md
│   │   └── S3_nl_full_template.md
│   ├── MC-FE-02/ ... MC-PY-04/       ← 12 个任务 × 9 个模板 = 108 个 prompt
│   └── README.md
├── generations/
│   ├── MC-FE-01/
│   │   ├── H_RRR/
│   │   │   ├── S1_architect.md
│   │   │   ├── S2_implementer.tsx
│   │   │   └── S3_auditor.tsx         ← 含审查报告 + 修复代码
│   │   ├── H_CRR/
│   │   ├── H_SRR/
│   │   ├── H_RCR/
│   │   ├── H_RSR/
│   │   ├── H_RRC/
│   │   ├── H_RRS/
│   │   ├── NLc_RRR/
│   │   ├── NLc_CRR/ ... NLc_RRS/
│   │   ├── NLf_RRR/
│   │   ├── NLf_CRR/ ... NLf_RRS/
│   │   └── (每任务 21 个子目录)
│   ├── MC-FE-02/ ... MC-PY-04/
│   └── robustness/                    ← Robustness check 重复
│       ├── H_RRR_run2/
│       └── H_RCR_run2/
├── analysis/
│   ├── constraint_binary.csv          ← L-A 二值层：每管线每约束 1/0
│   ├── semantic_adherence.csv         ← L-B 主观层：每管线 1-5
│   ├── decay_trace.csv                ← 每管线每 stage 的三指标
│   ├── token_counts.csv               ← 每管线每 stage token 统计
│   ├── functionality_scores.csv       ← L4 功能分
│   ├── stage_attribution.csv          ← L5 差值分析
│   └── robustness_check.csv           ← 重复测量结果
├── scoring_rules/
│   └── objective_rules.md             ← Appendix A：全部 72 条二值判定规则
└── EXP_C_RESULTS.md                   ← 最终分析报告
```

---

## 10. 工作量估算

| 步骤 | 耗时 | 谁做 |
|------|------|------|
| Prompt 模板完善（12 任务 × 9 套 = 108 个 prompt） | 3-4 小时 | 我 |
| 执行指令文档生成 | 1 小时 | 我 |
| Phase 1: 所有 S1（252 会话） | 6-8 小时 | 你粘贴 prompt（分三轮切换模型） |
| 中间处理：S1→S2 prompt 嵌入 | 1-2 小时 | 我（或脚本自动化） |
| Phase 2: 所有 S2（252 会话） | 6-8 小时 | 你 |
| 中间处理：S2→S3 prompt 嵌入 | 1-2 小时 | 我 |
| Phase 3: 所有 S3（252 会话） | 6-8 小时 | 你 |
| Phase 4: Robustness Check（48 管线 × 3） | 3-4 小时 | 你 |
| 审查 + 二值判定 + 分析 + 写作 | 4-6 小时 | 我 |
| **总计** | **约 5-7 天** | 你约 25-30 小时操作 |

---

## 11. 风险和缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 756 次调用 token 用量大 | 中 | 用户确认 token 充足；如需缩减可砍掉 RRS 和 SRR（最不关键的两组）→ 减少 2/7 成本 |
| S1 输出超过 2000 字 | 中 | Prompt 中已限制；如超出则手工截断到关键部分 |
| DeepSeek S2 生成中断 | 高 | 这本身是数据（H-C4 的 S 类型效应）；记录中断情况，不重跑 |
| Kimi S2 克隆出默认实现 | 高 | 这本身是数据（收敛型行为验证）；12 个任务中应能观察到差异 |
| NL-compact 与 Header token 数不完全对齐 | 中 | 手工调整 NL-c 措辞使两者 ±10% 以内；token 差值在 L3 中显式报告 |
| 252 个管线管理复杂 | 高 | 严格的目录命名 + 自动化脚本生成 prompt → 降低人工出错 |
| S3 不给修复代码只给审查意见 | 中 | Prompt 明确要求完整修复代码；如不给标记为"Auditor 未修复" |

---

## 12. 可削减方案（如时间/成本不足）

如果 756+144 = 900 次调用超出预算，以下是优先级排序的削减方案：

| 削减方案 | 削减内容 | 剩余管线 | 剩余调用 | 牺牲 |
|---------|---------|---------|---------|------|
| **Tier 0**（无削减） | 完整 7 组 + 3 编码 + 12 任务 + Robustness | 252 + 48 = 300 | 900 | 无 |
| **Tier 1** | 砍 Robustness Check | 252 | 756 | 失去稳定性验证 |
| **Tier 2** | 砍 RRS + SRR（S3/S1 的 S 类型） | 252 − 72 = 180 | 540 | 失去 S 类型在 S1/S3 的数据；保留核心 S2 ablation |
| **Tier 3** | 进一步砍 NL-full（只保留 NL-c vs H） | 180 × 2/3 = 120 | 360 | 失去冗余度效应的验证 |
| **Tier 4**（最低可行） | 只保留 RRR/CRR/RCR/RRC × NL-c/H × 12 | 96 | 288 | 仅保留 C 类型单变量 ablation |

推荐：**Tier 0 或 Tier 1**。Tier 2 以下开始牺牲研究完整性。

---

*设计完成：2026-04-01 18:49 CST (v3.1)*  
*修订基础：v3 + 叙事重定向（RQ-P: constraint decay via naturalization） + 相关文献定位*  
*待确认后进入 prompt 模板完善和执行指令生成阶段*
