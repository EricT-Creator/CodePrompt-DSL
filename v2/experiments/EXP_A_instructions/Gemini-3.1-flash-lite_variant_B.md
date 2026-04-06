# EXP-A 批量生成指令：Gemini-3.1-flash-lite - 变体 B

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

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/FE-05_DraggableSortList.tsx`

**Prompt**：
```
{
  "language": "TypeScript",
  "framework": "React",
  "style": "plain_css",
  "dependencies": "none",
  "constraints": ["no_html5_drag_api", "no_dragstart", "no_dragover", "no_drop", "mouse_touch_events_only"],
  "output": "export_default",
  "format": "code_only",
  "task": "Sortable list component with drag-and-drop reordering using mouse/touch events. Render at least 5 items with visual feedback (placeholder/ghost) during drag."
}
```

---

### 任务 2/12：FE-06_VirtualScrollTable

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/FE-06_VirtualScrollTable.tsx`

**Prompt**：
```
{
  "language": "TypeScript",
  "framework": "React",
  "style": "css_modules",
  "dependencies": "none",
  "constraints": ["no_react_window", "no_react_virtualized", "no_tailwind", "no_inline_styles"],
  "output": "export_default",
  "format": "code_only",
  "task": "Virtual scrolling table for 10000 rows with fixed header, 3 sortable columns, and overscan buffer. Only render visible rows. Include CSS module content as comment block."
}
```

---

### 任务 3/12：FE-07_CollaborativeWhiteboard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/FE-07_CollaborativeWhiteboard.tsx`

**Prompt**：
```
{
  "language": "TypeScript",
  "framework": "React",
  "style": "plain_css",
  "dependencies": "none",
  "constraints": ["no_canvas_lib", "no_fabric", "no_konva", "state_useReducer_only", "no_useState"],
  "output": "export_default",
  "format": "code_only",
  "task": "Canvas drawing whiteboard with pen, eraser, color picker (5+ colors), brush size control, undo/redo, and clear canvas. All state via useReducer."
}
```

---

### 任务 4/12：FE-08_MultiStepFormWizard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/FE-08_MultiStepFormWizard.tsx`

**Prompt**：
```
{
  "language": "TypeScript",
  "framework": "React",
  "style": "plain_css",
  "dependencies": "none",
  "constraints": ["no_form_lib", "no_react_hook_form", "no_formik", "no_zod", "no_yup", "validation_runtime_only"],
  "output": "export_default",
  "format": "code_only",
  "task": "3-step form wizard: Step1=Personal(name,email), Step2=Address(street,city,zip), Step3=Review. Next/back nav, per-step validation, preserve data on back, submit logs to console."
}
```

---

### 任务 5/12：BE-05_JWTAuthMiddleware

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/BE-05_JWTAuthMiddleware.py`

**Prompt**：
```
{
  "language": "Python",
  "framework": "FastAPI",
  "output": "single_file",
  "dependencies": ["fastapi", "uvicorn"],
  "constraints": ["no_pyjwt", "no_python_jose", "no_jwt_lib", "manual_jwt_via_hmac_base64", "stdlib_crypto_only"],
  "format": "code_only",
  "task": "JWT auth: POST /login (username/password -> token), GET /protected (require valid JWT), POST /refresh (renew token), 401 for invalid/expired, 30min expiry."
}
```

---

### 任务 6/12：BE-06_WebSocketChat

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/BE-06_WebSocketChat.py`

**Prompt**：
```
{
  "language": "Python",
  "framework": "FastAPI",
  "output": "single_file",
  "dependencies": ["fastapi", "uvicorn"],
  "constraints": ["no_async_queue_lib", "broadcast_via_set_iteration"],
  "format": "code_only",
  "task": "WebSocket chat server: multi-room, broadcast, nicknames, GET /rooms with user counts, in-memory history (last 50 per room), cleanup on disconnect."
}
```

---

### 任务 7/12：BE-07_RateLimiter

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/BE-07_RateLimiter.py`

**Prompt**：
```
{
  "language": "Python",
  "framework": "FastAPI",
  "output": "single_file",
  "dependencies": ["fastapi", "uvicorn"],
  "constraints": ["no_redis", "no_ratelimit_lib", "algorithm_token_bucket", "stdlib_only_for_logic"],
  "format": "code_only",
  "task": "Token Bucket rate limiter middleware: configurable rate/burst, per-IP tracking, 429 + Retry-After header, IP whitelist bypass, GET /status showing token count for requester IP."
}
```

---

### 任务 8/12：BE-08_BatchImportAPI

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/BE-08_BatchImportAPI.py`

**Prompt**：
```
{
  "language": "Python",
  "framework": "FastAPI",
  "output": "single_file",
  "dependencies": ["fastapi", "uvicorn"],
  "constraints": ["no_pandas", "use_csv_stdlib", "validation_strict", "streaming_response"],
  "format": "code_only",
  "task": "CSV batch import: POST /import (file upload), csv.reader parsing, validate name/email/age per row, StreamingResponse for line-by-line results, summary counts, GET /data for all records."
}
```

---

### 任务 9/12：PY-05_ConcurrentDownloader

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/PY-05_ConcurrentDownloader.py`

**Prompt**：
```
{
  "language": "Python",
  "dependencies": "stdlib_only",
  "constraints": ["no_requests", "no_httpx", "no_aiohttp", "use_urllib", "use_threading", "no_asyncio"],
  "output": "script",
  "format": "code_only",
  "task": "Concurrent downloader: URL list + output dir, ThreadPoolExecutor (configurable max_workers=4), retry with exponential backoff (max 3), timeout 30s, progress callback, return summary dict."
}
```

---

### 任务 10/12：PY-06_DAGScheduler

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/PY-06_DAGScheduler.py`

**Prompt**：
```
{
  "language": "Python",
  "dependencies": "stdlib_only",
  "constraints": ["no_networkx", "no_graphlib", "output_class"],
  "output": "script",
  "format": "code_only",
  "task": "DAG scheduler class: add_task(name,func), add_dependency(task,depends_on), validate() with CycleError, get_execution_order() topological sort, get_parallel_groups() sets of parallel tasks, execute() runs all."
}
```

---

### 任务 11/12：PY-07_TemplateEngine

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/PY-07_TemplateEngine.py`

**Prompt**：
```
{
  "language": "Python",
  "dependencies": "stdlib_only",
  "constraints": ["no_jinja2", "no_mako", "no_template_lib", "parser_regex_only", "no_ast_module"],
  "output": "script",
  "format": "code_only",
  "task": "Template engine: {{var}} substitution, {% if %}...{% endif %}, {% for item in list %}...{% endfor %}, nested blocks, filters (|upper|lower|title), render(template,context), TemplateSyntaxError."
}
```

---

### 任务 12/12：PY-08_ASTCodeChecker

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Gemini-3.1-flash-lite/B/PY-08_ASTCodeChecker.py`

**Prompt**：
```
{
  "language": "Python",
  "dependencies": "stdlib_only",
  "constraints": ["must_use_ast_module", "must_use_NodeVisitor_or_walk", "output_dataclass", "no_regex_for_analysis"],
  "output": "script",
  "format": "code_only",
  "task": "AST code checker: check_code(source) -> CheckResults dataclass. Detect: unused imports, unused variables, functions >50 lines, nesting >4 levels. Use ast.NodeVisitor."
}
```

