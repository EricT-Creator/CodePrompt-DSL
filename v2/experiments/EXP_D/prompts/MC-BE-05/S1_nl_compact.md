You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. stdlib + fastapi + uvicorn only. DO NOT use Python logging module — use print() with custom dict format for all logging. DO NOT use Pydantic BaseModel — use raw dict and manual validation. Single file. Code only.

Include:
1. CRUD endpoint design for items
2. Request logging architecture (print-based, NOT logging module)
3. Manual validation approach (NO Pydantic BaseModel)
4. Log storage and filtering
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI app with CRUD for items (POST /items, GET /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}) stored in memory. Include request logging for every endpoint call (method, path, timestamp, status_code, response_time_ms) stored in a memory list. GET /logs returns all logs. GET /logs?level=error filters by log level. Items have id, name, price, and category fields.
