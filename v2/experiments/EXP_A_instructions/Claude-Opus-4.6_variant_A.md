# EXP-A 批量生成指令：Claude-Opus-4.6 - 变体 A

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

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/FE-05_DraggableSortList.tsx`

**Prompt**：
```
Write a React component using TypeScript. Use plain CSS only (no Tailwind, no CSS modules, no styled-components). Do not use any external libraries. Do not use the HTML5 Drag and Drop API (no dragstart, dragover, drop events). Implement drag-and-drop reordering using only mouse and touch events (mousedown, mousemove, mouseup, touchstart, touchmove, touchend). The component should render a sortable list of at least 5 items with visual feedback during drag (e.g., placeholder or ghost element). Export as default. Output code only, no explanation.
```

---

### 任务 2/12：FE-06_VirtualScrollTable

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/FE-06_VirtualScrollTable.tsx`

**Prompt**：
```
Write a React component using TypeScript. Use CSS modules for styling (import styles from './VirtualScrollTable.module.css' - include the CSS as a comment block at the end of the file). No Tailwind, no inline styles. Do not use any external libraries (no react-window, no react-virtualized). Implement a virtual scrolling table that efficiently renders 10000 rows. The table must have: a fixed header row, at least 3 sortable columns (click header to sort), virtual scrolling that only renders visible rows plus an overscan buffer. Export as default. Output code only, no explanation.
```

---

### 任务 3/12：FE-07_CollaborativeWhiteboard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/FE-07_CollaborativeWhiteboard.tsx`

**Prompt**：
```
Write a React component using TypeScript. Use plain CSS only (no Tailwind). Do not use any external libraries (no fabric.js, no konva, no p5). All state must be managed with useReducer only (do not use useState anywhere). Implement a canvas-based drawing whiteboard with: pen tool (freehand drawing), eraser tool, color picker (at least 5 colors), adjustable brush size, undo and redo functionality, clear canvas button. Export as default. Output code only, no explanation.
```

---

### 任务 4/12：FE-08_MultiStepFormWizard

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/FE-08_MultiStepFormWizard.tsx`

**Prompt**：
```
Write a React component using TypeScript. Use plain CSS only (no Tailwind). Do not use any external libraries (no react-hook-form, no formik, no zod, no yup). Implement a 3-step form wizard: Step 1 - Personal info (name required, email with format validation), Step 2 - Address (street, city, zip code all required), Step 3 - Review & confirm (display all entered data). Requirements: next/back navigation between steps, per-step validation before advancing, back navigation must preserve entered data, final submit button on step 3 that logs all data to console. Export as default. Output code only, no explanation.
```

---

### 任务 5/12：BE-05_JWTAuthMiddleware

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/BE-05_JWTAuthMiddleware.py`

**Prompt**：
```
Write a Python FastAPI application in a single file. Use only the standard library plus fastapi and uvicorn (no PyJWT, no python-jose, no third-party JWT libraries). Implement JWT authentication manually using hmac and base64 from the standard library. The app must have: POST /login accepting username/password and returning a JWT token, GET /protected that requires a valid JWT in the Authorization header, POST /refresh that accepts a valid token and returns a new one, proper 401 responses for invalid/expired tokens, token expiry set to 30 minutes. Output code only, no explanation.
```

---

### 任务 6/12：BE-06_WebSocketChat

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/BE-06_WebSocketChat.py`

**Prompt**：
```
Write a Python FastAPI application in a single file. Use only fastapi and uvicorn as dependencies. Implement a WebSocket chat server with: multiple chat rooms (join by room name in URL path), broadcast messages to all users in the same room, user nicknames (sent as first message after connect), GET /rooms endpoint listing active rooms with user counts, in-memory message history (last 50 messages per room), proper connection cleanup on disconnect. Output code only, no explanation.
```

---

### 任务 7/12：BE-07_RateLimiter

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/BE-07_RateLimiter.py`

**Prompt**：
```
Write a Python FastAPI application in a single file. Use only fastapi, uvicorn, and the standard library (no Redis, no third-party rate limit libraries). Implement a Token Bucket rate limiting middleware with: configurable rate (tokens per second) and burst (max tokens), per-IP tracking, 429 Too Many Requests response with Retry-After header showing seconds until next available token, a whitelist of IPs that bypass rate limiting, GET /status endpoint showing current token count for the requester's IP. Output code only, no explanation.
```

---

### 任务 8/12：BE-08_BatchImportAPI

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/BE-08_BatchImportAPI.py`

**Prompt**：
```
Write a Python FastAPI application in a single file. Use only fastapi, uvicorn, and the standard library (no pandas). Implement a CSV batch import endpoint: POST /import accepts a CSV file upload, parse each row using the csv standard library module, validate each row (name: non-empty string, email: valid format with @ and dot, age: integer 0-150), store valid rows in an in-memory list of dicts, use StreamingResponse to return results line-by-line as they are processed, final summary line with counts: total, success, failed, skipped. Include GET /data to retrieve all imported records. Output code only, no explanation.
```

---

### 任务 9/12：PY-05_ConcurrentDownloader

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/PY-05_ConcurrentDownloader.py`

**Prompt**：
```
Write a Python script. Use only the standard library (no requests, no httpx, no aiohttp). Use urllib.request for HTTP downloads. Use threading and ThreadPoolExecutor for concurrency (no asyncio). Implement a concurrent file downloader with: a download function accepting a list of URLs and output directory, configurable max_workers (default 4), retry logic with exponential backoff (max 3 retries), configurable timeout per request (default 30s), a progress callback function called after each download completes, return a summary dict with succeeded/failed counts and error details. Output code only, no explanation.
```

---

### 任务 10/12：PY-06_DAGScheduler

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/PY-06_DAGScheduler.py`

**Prompt**：
```
Write a Python script. Use only the standard library (no networkx, no graphlib). Implement a DAG task scheduler as a class with: add_task(name, func) to register tasks, add_dependency(task, depends_on) to declare edges, validate() that detects circular dependencies and raises CycleError, get_execution_order() returning a topological sort, get_parallel_groups() returning list of sets where tasks in each set can run in parallel, execute() that runs all tasks respecting dependencies. Include a CycleError exception class. Output code only, no explanation.
```

---

### 任务 11/12：PY-07_TemplateEngine

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/PY-07_TemplateEngine.py`

**Prompt**：
```
Write a Python script. Use only the standard library (no jinja2, no mako, no any template library). Use regular expressions for parsing (no ast module for template parsing). Implement a simple template engine with: variable substitution {{variable}}, conditional blocks {% if condition %}...{% endif %}, for loops {% for item in list %}...{% endfor %}, nested block support (if inside for, etc.), filter pipes {{variable|upper}} {{variable|lower}} {{variable|title}}, a render(template_string, context_dict) function, raise TemplateSyntaxError for malformed templates. Output code only, no explanation.
```

---

### 任务 12/12：PY-08_ASTCodeChecker

**保存路径**：`/Users/erichztang/Downloads/古文运动/v2/generations/Claude-Opus-4.6/A/PY-08_ASTCodeChecker.py`

**Prompt**：
```
Write a Python script. Use only the standard library. You MUST use the ast module (ast.parse, ast.NodeVisitor or ast.walk) for code analysis. All check results must be returned as dataclass instances. Implement a code checker that accepts a Python source string and detects: unused imports (imported but never referenced), unused variables (assigned but never read), functions longer than 50 lines, nesting deeper than 4 levels (if/for/while/with/try). Provide a check_code(source: str) -> CheckResults function. The CheckResults dataclass should contain lists of issues found. Output code only, no explanation.
```

