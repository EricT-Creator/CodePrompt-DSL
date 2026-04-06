# EXP-A 批量生成指令：DeepSeek-V3.2 - 变体 C

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

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/FE-05_DraggableSortList.tsx`

**Prompt**：
```
[L]TS [F]React [S]plain_css [D]none [X]no_html5_drag,no_dragstart,no_dragover,no_drop,mouse_touch_only [O]export_default [OUT]code_only
Sortable list with drag-and-drop reorder via mousedown/mousemove/mouseup and touch events. Min 5 items, visual feedback during drag.
```

---

### 任务 2/12：FE-06_VirtualScrollTable

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/FE-06_VirtualScrollTable.tsx`

**Prompt**：
```
[L]TS [F]React [S]css_modules [D]none [X]no_react_window,no_react_virtualized,no_tailwind,no_inline [O]export_default [OUT]code_only
Virtual scroll table for 10000 rows. Fixed header, 3 sortable columns, only render visible rows + overscan. CSS module as comment block at end.
```

---

### 任务 3/12：FE-07_CollaborativeWhiteboard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/FE-07_CollaborativeWhiteboard.tsx`

**Prompt**：
```
[L]TS [F]React [S]plain_css [D]none [X]no_canvas_lib,no_fabric,no_konva,useReducer_only,no_useState [O]export_default [OUT]code_only
Canvas whiteboard: pen, eraser, color picker (5+ colors), brush size, undo/redo, clear. All state via useReducer.
```

---

### 任务 4/12：FE-08_MultiStepFormWizard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/FE-08_MultiStepFormWizard.tsx`

**Prompt**：
```
[L]TS [F]React [S]plain_css [D]none [X]no_form_lib,no_rhf,no_formik,no_zod,no_yup,manual_validation [O]export_default [OUT]code_only
3-step form wizard: 1)Personal(name+email validation) 2)Address(street+city+zip required) 3)Review+submit. Next/back nav, preserve data, console.log on submit.
```

---

### 任务 5/12：BE-05_JWTAuthMiddleware

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/BE-05_JWTAuthMiddleware.py`

**Prompt**：
```
[L]Python [F]FastAPI [D]fastapi,uvicorn [X]no_pyjwt,no_jose,manual_jwt_hmac_base64,stdlib_only [O]single_file [OUT]code_only
JWT auth middleware: POST /login -> token, GET /protected -> require JWT, POST /refresh -> new token. 401 on invalid/expired. 30min expiry. Manual HMAC-SHA256 signing.
```

---

### 任务 6/12：BE-06_WebSocketChat

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/BE-06_WebSocketChat.py`

**Prompt**：
```
[L]Python [F]FastAPI [D]fastapi,uvicorn [X]no_async_queue,broadcast_via_set [O]single_file [OUT]code_only
WebSocket chat: multi-room (room in URL), broadcast to room, nicknames (first msg), GET /rooms (active rooms + counts), history (last 50/room), cleanup on disconnect.
```

---

### 任务 7/12：BE-07_RateLimiter

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/BE-07_RateLimiter.py`

**Prompt**：
```
[L]Python [F]FastAPI [D]fastapi,uvicorn [X]no_redis,no_ratelimit_lib,token_bucket_algo,stdlib_only [O]single_file [OUT]code_only
Token Bucket rate limiter: configurable rate/burst, per-IP, 429 + Retry-After header, IP whitelist bypass, GET /status shows requester's token count.
```

---

### 任务 8/12：BE-08_BatchImportAPI

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/BE-08_BatchImportAPI.py`

**Prompt**：
```
[L]Python [F]FastAPI [D]fastapi,uvicorn [X]no_pandas,use_csv_stdlib,strict_validation,streaming_response [O]single_file [OUT]code_only
CSV batch import: POST /import (file upload), csv parsing, validate (name non-empty, email format, age 0-150), StreamingResponse line-by-line, summary counts (total/success/failed), GET /data.
```

---

### 任务 9/12：PY-05_ConcurrentDownloader

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/PY-05_ConcurrentDownloader.py`

**Prompt**：
```
[L]Python [D]stdlib_only [X]no_requests,no_httpx,no_aiohttp,use_urllib,use_threading,no_asyncio [O]script [OUT]code_only
Concurrent downloader: URL list + output dir, ThreadPoolExecutor(max_workers=4), retry with exp backoff(max 3), timeout 30s, progress callback, summary dict(succeeded/failed/errors).
```

---

### 任务 10/12：PY-06_DAGScheduler

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/PY-06_DAGScheduler.py`

**Prompt**：
```
[L]Python [D]stdlib_only [X]no_networkx,no_graphlib,class_output [O]script [OUT]code_only
DAG scheduler class: add_task(name,func), add_dependency(task,depends_on), validate()->CycleError, get_execution_order()->topo sort, get_parallel_groups()->list of parallel sets, execute().
```

---

### 任务 11/12：PY-07_TemplateEngine

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/PY-07_TemplateEngine.py`

**Prompt**：
```
[L]Python [D]stdlib_only [X]no_jinja,no_mako,no_template_lib,regex_parser,no_ast [O]script [OUT]code_only
Template engine: {{var}}, {% if cond %}...{% endif %}, {% for x in list %}...{% endfor %}, nested blocks, filters (|upper|lower|title), render(template,context), TemplateSyntaxError.
```

---

### 任务 12/12：PY-08_ASTCodeChecker

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/DeepSeek-V3.2/C/PY-08_ASTCodeChecker.py`

**Prompt**：
```
[L]Python [D]stdlib_only [X]must_use_ast,must_use_NodeVisitor,output_dataclass,no_regex_analysis [O]script [OUT]code_only
AST code checker: check_code(source)->CheckResults dataclass. Detect: unused imports, unused vars, funcs >50 lines, nesting >4 levels.
```

