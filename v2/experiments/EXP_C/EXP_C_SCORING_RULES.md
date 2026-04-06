# EXP-C Scoring Rules: Objective Binary Constraint Check (Appendix A)

> **版本**：v1.0 | **日期**：2026-04-01  
> **用途**：对 S2/S3 代码产物的每条约束做 Satisfied(1) / Not Satisfied(0) 判定  
> **判定原则**：规则必须可程序化——给定源代码和本规则表，任何人用 grep/AST 工具能得到相同结果  
> **总规则数**：12 任务 × 6 约束 = 72 条

---

## 判定总则

- **Satisfied (1)**：代码同时满足"正面检查"和"负面排除"
- **Not Satisfied (0)**：代码违反"正面检查"或"负面排除"中的任意一项
- **N/A**：文件缺失或为空（此时整管线 CSR = 0）

---

## MC-FE-01: Real-time Collaborative Todo Board

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | TS + React | ❌ | 文件为 `.tsx`；包含 `React` import 或 JSX 语法 | 文件非 `.tsx` 或无 React 痕迹 |
| C2 | CSS Modules, 禁 Tailwind | ✅ | 包含 `styles.xxx` 或 `.module.css` 引用；不包含 `className="flex` / `className="bg-` 等 Tailwind 类名模式 | 包含 `tailwind` import 或 utility class 模式 |
| C3 | HTML5 原生拖拽, 禁 dnd 库 | ✅ | 包含 `onDragStart`/`onDragOver`/`onDrop` handler；不包含 `react-dnd`/`dnd-kit`/`@hello-pangea` import | 包含任何 dnd 库 import |
| C4 | useReducer only | ❌ | 包含 `useReducer`；不包含 `redux`/`zustand`/`jotai` import | 缺少 `useReducer` 或包含状态库 import |
| C5 | 单文件 export default | ❌ | 包含 `export default`；文件无多文件分隔符 | 缺少 `export default` |
| C6 | 手写 WS mock, 禁 socket.io | ❌ | 包含 `setTimeout`/`setInterval` 用于模拟同步；不包含 `socket.io` import | 包含 `socket.io` import 或无同步模拟 |

## MC-FE-02: Virtual Scroll Data Grid

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | TS + React | ❌ | `.tsx` + React import/JSX | 同 MC-FE-01.C1 |
| C2 | 手写虚拟滚动, 禁 windowing 库 | ✅ | 包含 `scrollTop`/`scrollHeight` 计算逻辑或 `onScroll` handler；不包含 `react-window`/`react-virtualized`/`@tanstack/virtual` import | 包含任何 windowing 库 import |
| C3 | CSS Modules, 禁 Tailwind/inline | ✅ | 包含 `styles.xxx` 或 `.module.css`；不包含 Tailwind 类名模式；不包含大量 `style={{` inline 写法（允许个别动态 style） | 主要使用 Tailwind 或 inline style |
| C4 | 无外部依赖 | ❌ | import 语句仅含 `react` / `react-dom` | 包含第三方 npm 包 import |
| C5 | 单文件 export default | ❌ | 包含 `export default` | 缺少 `export default` |
| C6 | 数据内嵌 | ❌ | mock 数据在文件内生成（`Array.from` / 硬编码数组等）；不从外部文件 import 数据 | 从外部文件 import 数据 |

## MC-FE-03: Canvas Drawing Whiteboard

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | TS + React | ❌ | `.tsx` + React import/JSX | 同 MC-FE-01.C1 |
| C2 | 手写 Canvas 2D, 禁 canvas 库 | ✅ | 包含 `getContext('2d')` 或 `CanvasRenderingContext2D`；不包含 `fabric`/`konva`/`p5` import | 包含任何 canvas 库 import |
| C3 | useReducer only, 禁 useState | ✅ | 包含 `useReducer`；不包含 `useState` 调用（`React.useState` 亦视为违反） | 包含 `useState` 或缺少 `useReducer` |
| C4 | 无外部依赖 | ❌ | import 仅含 `react` / `react-dom` | 包含第三方包 import |
| C5 | 单文件 export default | ❌ | 包含 `export default` | 缺少 `export default` |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

## MC-FE-04: Multi-Step Form Wizard

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | TS + React | ❌ | `.tsx` + React import/JSX | 同 MC-FE-01.C1 |
| C2 | 手写验证, 禁 form/validation 库 | ✅ | 包含手写验证逻辑（regex/条件判断等）；不包含 `react-hook-form`/`formik`/`zod`/`yup` import | 包含任何表单/验证库 import |
| C3 | plain CSS, 禁 Tailwind | ✅ | 使用 `<style>` 标签或 CSS class 字符串；不包含 Tailwind 类名模式 | 包含 Tailwind 类名模式 |
| C4 | 无外部依赖 | ❌ | import 仅含 `react` / `react-dom` | 包含第三方包 import |
| C5 | 单文件 export default | ❌ | 包含 `export default` | 缺少 `export default` |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

---

## MC-BE-01: Event-Sourced Task Queue API

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python + FastAPI | ❌ | `.py` 文件；包含 `from fastapi` / `import fastapi` | 非 `.py` 或无 FastAPI import |
| C2 | stdlib + fastapi + uvicorn only | ❌ | import 仅含标准库 + `fastapi` + `uvicorn` + `pydantic`（FastAPI 自动依赖） | 包含 `sqlalchemy`/`aiohttp`/`requests` 等第三方 import |
| C3 | asyncio.Queue, 禁 Celery/RQ | ✅ | 包含 `asyncio.Queue()` 实例化；不包含 `celery`/`rq` import | 缺少 `asyncio.Queue` 或包含 celery/rq |
| C4 | append-only list event store | ✅ | 事件存储使用 `.append()`；不存在 `del events[`/`events.pop(`/`events[i] =` 修改操作 | 存在覆盖/删除/修改事件的代码 |
| C5 | 所有端点幂等 | ❌ | POST 端点包含 idempotency key 参数或检查逻辑 | 无幂等机制 |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

## MC-BE-02: JWT Auth Middleware

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python + FastAPI | ❌ | `.py` + FastAPI import | 同 MC-BE-01.C1 |
| C2 | 手写 JWT, 禁 PyJWT/jose | ✅ | 包含 `hmac`/`base64` 的 JWT 签名逻辑；不包含 `jwt`/`jose`/`PyJWT` import | 包含 JWT 库 import |
| C3 | stdlib + fastapi + uvicorn | ✅ | import 仅含标准库 + fastapi + uvicorn + pydantic | 包含其他第三方包 |
| C4 | 单文件 | ❌ | 所有代码在一个 `.py` 文件中 | 多文件结构 |
| C5 | login/protected/refresh 端点 | ❌ | 包含 `/login`、`/protected`（或类似 protected 路由）、`/refresh` 路由 | 缺少任一端点 |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

## MC-BE-03: WebSocket Chat Server

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python + FastAPI | ❌ | `.py` + FastAPI import | 同 MC-BE-01.C1 |
| C2 | 禁 asyncio.Queue 广播, 用 set 遍历 | ✅ | 广播实现为 `for conn in connections:` 遍历；不使用 `asyncio.Queue()` 用于广播 | 使用 `asyncio.Queue` 做广播 |
| C3 | fastapi + uvicorn only | ✅ | import 仅含 fastapi + uvicorn + 标准库 | 包含其他第三方包 |
| C4 | 单文件 | ❌ | 所有代码在一个 `.py` 文件中 | 多文件结构 |
| C5 | 消息历史 list ≤100 条 | ❌ | 包含消息历史 list 且有长度限制逻辑（如 `if len(history) > 100` 或 `deque(maxlen=100)`） | 无消息历史或无长度限制 |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

## MC-BE-04: Rate Limiter Middleware

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python + FastAPI | ❌ | `.py` + FastAPI import | 同 MC-BE-01.C1 |
| C2 | Token Bucket 算法, 禁简单计数器 | ✅ | 包含 token/bucket 相关变量名且有补充令牌逻辑（基于时间差）；不是简单 `count += 1` 模式 | 使用简单计数器/固定窗口 |
| C3 | stdlib + fastapi, 禁 Redis | ✅ | 不包含 `redis`/`memcached` import；存储使用内存 dict | 包含 Redis/memcached |
| C4 | 单文件 | ❌ | 所有代码在一个 `.py` 文件中 | 多文件结构 |
| C5 | 429 + Retry-After + 白名单 | ❌ | 包含 429 状态码返回；包含 `Retry-After` header；包含 whitelist 检查 | 缺少 429/Retry-After/whitelist 任一 |
| C6 | 纯代码输出 | ❌ | 文件不含 markdown 围栏/解释段落 | 包含非代码内容 |

---

## MC-PY-01: Plugin-based Data Pipeline

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python 3.10+, stdlib only | ❌ | `.py` 文件；import 仅含标准库模块 | 包含第三方 import |
| C2 | exec() 加载, 禁 importlib | ✅ | 包含 `exec(` 调用用于加载插件代码；不包含 `importlib` import | 使用 importlib 或无 exec |
| C3 | Protocol 接口, 禁 ABC | ✅ | 包含 `Protocol` 定义；不包含 `ABC`/`abstractmethod` import | 使用 ABC 或无接口定义 |
| C4 | 完整类型标注 | ❌ | 所有 public 方法有参数和返回值类型标注 | public 方法缺少类型标注 |
| C5 | 错误隔离 | ❌ | 包含 try/except 在单插件执行层（非全局 catch all） | 无错误隔离或单插件异常会 crash 整体 |
| C6 | 单文件 class | ❌ | 包含 `class Pipeline` 或类似主 class；单文件 | 无 class 或多文件 |

## MC-PY-02: DAG Task Scheduler

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python 3.10+, stdlib only | ❌ | `.py`；import 仅含标准库 | 包含第三方 import |
| C2 | 禁 networkx/graphlib | ✅ | 不包含 `networkx`/`graphlib` import；拓扑排序为手写（含 in-degree 计算或 DFS 标记） | 包含 graph 库 import |
| C3 | 输出为 class | ✅ | 包含 `class DAGScheduler` 或类似名称的 class | 无 class，只有函数 |
| C4 | 完整类型标注 | ❌ | 所有 public 方法有类型标注 | 缺少类型标注 |
| C5 | CycleError 自定义异常 | ❌ | 包含 `class CycleError` 定义且在环检测时 raise | 无 CycleError 定义或不 raise |
| C6 | 单文件 | ❌ | 单文件 | 多文件 |

## MC-PY-03: Template Engine

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python 3.10+, stdlib only | ❌ | `.py`；import 仅含标准库 | 包含第三方 import |
| C2 | 正则解析, 禁 jinja2/mako | ✅ | 包含 `re.compile` 或 `re.findall`/`re.sub` 用于模板解析；不包含 `jinja2`/`mako` import | 包含模板库 import |
| C3 | 禁 ast 模块 | ✅ | 不包含 `import ast` 或 `ast.` 调用 | 包含 ast 使用 |
| C4 | 完整类型标注 | ❌ | 所有 public 方法有类型标注 | 缺少类型标注 |
| C5 | TemplateSyntaxError 自定义异常 | ❌ | 包含 `class TemplateSyntaxError` 且在解析错误时 raise | 无该异常或不 raise |
| C6 | 单文件 class | ❌ | 包含 `class TemplateEngine` 或类似 class；单文件 | 无 class 或多文件 |

## MC-PY-04: AST Code Checker

| # | 约束 | 反直觉 | Satisfied 规则 | Not Satisfied 规则 |
|---|------|--------|-------------|------------------|
| C1 | Python 3.10+, stdlib only | ❌ | `.py`；import 仅含标准库（`ast` 属于标准库，允许） | 包含第三方 import |
| C2 | 必须 ast.NodeVisitor, 禁正则 | ✅ | 包含 `ast.NodeVisitor` 子类或 `ast.walk` 调用；不使用 `re.` 做代码模式匹配 | 使用正则做代码检查或无 ast 使用 |
| C3 | dataclass 输出 | ✅ | 包含 `@dataclass` 装饰器用于结果封装 | 无 dataclass |
| C4 | 完整类型标注 | ❌ | 所有 public 方法有类型标注 | 缺少类型标注 |
| C5 | 四种检查全实现 | ❌ | 代码中可识别出：unused import 检查 + unused variable 检查 + function length 检查 + nesting depth 检查 | 缺少任一检查 |
| C6 | 单文件 class | ❌ | 包含 `class CodeChecker` 或类似 class；单文件 | 无 class 或多文件 |

---

## 快速参考：反直觉约束清单（24 条）

| 任务 | C? | 约束摘要 | 核心检测 |
|------|------|---------|---------|
| MC-FE-01 | C2 | CSS Modules, 禁 Tailwind | grep `tailwind` / utility class pattern |
| MC-FE-01 | C3 | HTML5 Drag, 禁 dnd 库 | grep `dnd-kit` / `react-dnd` |
| MC-FE-02 | C2 | 手写虚拟滚动 | grep `react-window` / `react-virtualized` |
| MC-FE-02 | C3 | CSS Modules, 禁 inline | grep Tailwind + inline `style={{` 频率 |
| MC-FE-03 | C2 | 手写 Canvas 2D | grep `fabric` / `konva` / `p5` |
| MC-FE-03 | C3 | useReducer only, 禁 useState | grep `useState` |
| MC-FE-04 | C2 | 手写验证 | grep `formik` / `react-hook-form` / `zod` / `yup` |
| MC-FE-04 | C3 | plain CSS | grep Tailwind class pattern |
| MC-BE-01 | C3 | asyncio.Queue | grep `celery` / `rq` |
| MC-BE-01 | C4 | append-only | grep `del events` / `events.pop` / `events[` assignment |
| MC-BE-02 | C2 | 手写 JWT | grep `jwt` / `jose` / `PyJWT` |
| MC-BE-02 | C3 | stdlib only | grep 第三方 import |
| MC-BE-03 | C2 | 禁 asyncio.Queue 广播 | grep `asyncio.Queue` 在广播上下文 |
| MC-BE-03 | C3 | fastapi only | grep 第三方 import |
| MC-BE-04 | C2 | Token Bucket | 检查令牌补充逻辑 |
| MC-BE-04 | C3 | 禁 Redis | grep `redis` |
| MC-PY-01 | C2 | exec() 加载 | grep `importlib` |
| MC-PY-01 | C3 | Protocol, 禁 ABC | grep `ABC` / `abstractmethod` |
| MC-PY-02 | C2 | 禁 networkx/graphlib | grep `networkx` / `graphlib` |
| MC-PY-02 | C3 | class 输出 | grep `class ` |
| MC-PY-03 | C2 | 正则解析, 禁 jinja2 | grep `jinja2` / `mako` |
| MC-PY-03 | C3 | 禁 ast | grep `import ast` |
| MC-PY-04 | C2 | ast.NodeVisitor, 禁正则 | grep `re.` 在代码检查上下文 |
| MC-PY-04 | C3 | dataclass | grep `@dataclass` |

---

*Scoring Rules 版本：v1.0 | 最后更新：2026-04-01*
