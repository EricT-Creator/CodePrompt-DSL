You are a developer. Implement the technical design below as a single Python file (.py). Follow ALL engineering constraints below strictly. Output code only, no explanation.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. Do NOT import or use the Python `logging` module at all. Instead, implement all logging using print() with a custom dict format like print({"level": "INFO", "method": "POST", ...}).
4. Do NOT use Pydantic BaseModel for request/response models. Use raw Python dicts for data handling and implement manual validation (check key existence, type, value range) directly in endpoint functions.
5. All code in a single .py file.
6. Output code only, no explanation text.

Technical Design:
---
{S1_OUTPUT}
---
