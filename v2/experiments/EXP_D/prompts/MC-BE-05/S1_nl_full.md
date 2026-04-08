You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. Do NOT import or use the Python `logging` module at all. Instead, implement all logging using print() with a custom dict format like print({"level": "INFO", "method": "POST", ...}).
4. Do NOT use Pydantic BaseModel for request/response models. Use raw Python dicts for data handling and implement manual validation (check key existence, type, value range) directly in endpoint functions.
5. All code in a single .py file.
6. Output code only, no explanation text.

Include:
1. CRUD endpoint design for items
2. Request logging architecture (print-based, NOT logging module)
3. Manual validation approach (NO Pydantic BaseModel)
4. Log storage and filtering
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI app with CRUD for items (POST /items, GET /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}) stored in memory. Include request logging for every endpoint call (method, path, timestamp, status_code, response_time_ms) stored in a memory list. GET /logs returns all logs. GET /logs?level=error filters by log level. Items have id, name, price, and category fields.
