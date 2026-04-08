[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!LOG]NO_LOGGING_MODULE [!PYDANTIC]NO_BASEMODEL [FILE]SINGLE [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. CRUD endpoint design for items
2. Request logging architecture (print-based, NOT logging module)
3. Manual validation approach (NO Pydantic BaseModel)
4. Log storage and filtering
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI app with CRUD for items (POST /items, GET /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}) stored in memory. Include request logging for every endpoint call (method, path, timestamp, status_code, response_time_ms) stored in a memory list. GET /logs returns all logs. GET /logs?level=error filters by log level. Items have id, name, price, and category fields.
