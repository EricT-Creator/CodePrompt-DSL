# EXP-A 批量生成指令：GPT-5.4 - 变体 D

## 你的任务

请按照以下 12 个任务的 prompt，依次生成代码并保存到指定路径。
**每个任务单独生成一个文件，严格遵循 prompt 中的所有约束。**
**只输出代码，不要输出解释或说明。**

## 重要规则

1. 每个任务的代码必须保存为独立文件，路径如下方所示
2. 严格遵守每个 prompt 中的约束（语言、框架、禁用库等）
3. 每个文件必须是可直接运行/编译的完整代码
4. 不要在文件中包含 markdown 代码围栏
5. 如果 prompt 要求 export default，文件必须包含 export default

---

### 任务 1/12：FE-05_DraggableSortList

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/FE-05_DraggableSortList.tsx`

**Prompt**：
```
[语]TS [架]React [样]原生CSS [依]无 [禁]禁HTML5拖放API,须用鼠标触摸事件 [出]默认导出 [格]纯码
可拖拽排序列表，至少五项，拖动时有视觉反馈，放下后更新顺序。
```

---

### 任务 2/12：FE-06_VirtualScrollTable

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/FE-06_VirtualScrollTable.tsx`

**Prompt**：
```
[语]TS [架]React [样]CSS模块 [依]无 [禁]禁react-window/virtualized/Tailwind/内联样式 [出]默认导出 [格]纯码
万行虚拟滚动表格，固定表头，三列可排序，仅渲染可见行加缓冲区。CSS模块内容以注释块附于文件末尾。
```

---

### 任务 3/12：FE-07_CollaborativeWhiteboard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/FE-07_CollaborativeWhiteboard.tsx`

**Prompt**：
```
[语]TS [架]React [样]原生CSS [依]无 [禁]禁canvas库,禁useState须用useReducer [出]默认导出 [格]纯码
画布白板：画笔、橡皮擦、颜色选择(至少五色)、笔刷大小、撤销重做、清除画布。所有状态用useReducer管理。
```

---

### 任务 4/12：FE-08_MultiStepFormWizard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/FE-08_MultiStepFormWizard.tsx`

**Prompt**：
```
[语]TS [架]React [样]原生CSS [依]无 [禁]禁表单库,禁验证库,须手写校验 [出]默认导出 [格]纯码
三步表单向导：1)个人信息(姓名必填,邮箱格式校验) 2)地址(街道城市邮编必填) 3)确认并提交。支持前进后退，后退保留数据，提交时console.log全部数据。
```

---

### 任务 5/12：BE-05_JWTAuthMiddleware

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/BE-05_JWTAuthMiddleware.py`

**Prompt**：
```
[语]Python [架]FastAPI [依]fastapi,uvicorn [禁]禁PyJWT/jose等JWT库,须用hmac+base64手动实现 [出]单文件 [格]纯码
JWT认证：POST /login签发令牌，GET /protected验证令牌，POST /refresh刷新令牌。无效/过期返回401。有效期30分钟。手动HMAC-SHA256签名。
```

---

### 任务 6/12：BE-06_WebSocketChat

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/BE-06_WebSocketChat.py`

**Prompt**：
```
[语]Python [架]FastAPI [依]fastapi,uvicorn [禁]禁异步队列库,广播须遍历集合 [出]单文件 [格]纯码
WebSocket聊天服务：多房间(URL路径)，房间内广播，昵称(首条消息)，GET /rooms列出活跃房间及人数，内存消息历史(每房间最近50条)，断开时清理连接。
```

---

### 任务 7/12：BE-07_RateLimiter

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/BE-07_RateLimiter.py`

**Prompt**：
```
[语]Python [架]FastAPI [依]fastapi,uvicorn [禁]禁Redis,禁限流库,须实现令牌桶算法,仅标准库 [出]单文件 [格]纯码
令牌桶限流中间件：可配置速率/突发量，按IP追踪，429响应含Retry-After头，白名单IP跳过限流，GET /status显示请求者当前令牌数。
```

---

### 任务 8/12：BE-08_BatchImportAPI

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/BE-08_BatchImportAPI.py`

**Prompt**：
```
[语]Python [架]FastAPI [依]fastapi,uvicorn [禁]禁pandas,须用csv标准库,严格验证,流式响应 [出]单文件 [格]纯码
CSV批量导入：POST /import接收文件上传，csv解析，逐行验证(姓名非空、邮箱格式、年龄0-150)，StreamingResponse逐行返回处理状态，汇总计数(总数/成功/失败)，GET /data查看全部记录。
```

---

### 任务 9/12：PY-05_ConcurrentDownloader

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/PY-05_ConcurrentDownloader.py`

**Prompt**：
```
[语]Python [依]仅标准库 [禁]禁requests/httpx/aiohttp,须用urllib,须用threading,禁asyncio [出]脚本 [格]纯码
并发下载器：接收URL列表和输出目录，ThreadPoolExecutor(默认4线程)，指数退避重试(最多3次)，超时30秒，进度回调，返回汇总字典(成功/失败数及错误详情)。
```

---

### 任务 10/12：PY-06_DAGScheduler

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/PY-06_DAGScheduler.py`

**Prompt**：
```
[语]Python [依]仅标准库 [禁]禁networkx/graphlib,须实现为类 [出]脚本 [格]纯码
DAG任务调度器类：add_task(名称,函数)注册任务，add_dependency(任务,依赖)声明边，validate()检测环依赖抛CycleError，get_execution_order()拓扑排序，get_parallel_groups()返回可并行执行的任务组，execute()执行全部任务。
```

---

### 任务 11/12：PY-07_TemplateEngine

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/PY-07_TemplateEngine.py`

**Prompt**：
```
[语]Python [依]仅标准库 [禁]禁jinja2/mako等模板库,须用正则解析,禁ast模块 [出]脚本 [格]纯码
简易模板引擎：变量替换{{var}}，条件{% if %}...{% endif %}，循环{% for item in list %}...{% endfor %}，支持嵌套，过滤器(|upper|lower|title)，render(模板字符串,上下文字典)函数，格式错误抛TemplateSyntaxError。
```

---

### 任务 12/12：PY-08_ASTCodeChecker

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/GPT-5.4/D/PY-08_ASTCodeChecker.py`

**Prompt**：
```
[语]Python [依]仅标准库 [禁]须用ast模块和NodeVisitor,结果须用dataclass,禁正则分析 [出]脚本 [格]纯码
AST代码检查器：check_code(源码字符串)->CheckResults数据类。检测：未使用的import、未使用的变量、超过50行的函数、超过4层的嵌套。
```

