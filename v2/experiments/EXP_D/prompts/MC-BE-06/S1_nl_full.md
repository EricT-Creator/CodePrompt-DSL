You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. ALL route handler functions must be defined with `def`, NOT `async def`. FastAPI supports synchronous route handlers — use them exclusively.
4. Do NOT import or use pathlib at all. Use os.path module for all file path operations (os.path.exists, os.path.getsize, os.path.splitext, os.path.getmtime, os.path.isdir, etc.).
5. All code in a single .py file.
6. Output code only, no explanation text.

Include:
1. POST /metadata endpoint design
2. File metadata extraction approach (os.path, NOT pathlib)
3. Synchronous handler design (def, NOT async def)
4. Error handling for non-existent paths
5. GET /recent endpoint with in-memory tracking
6. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI app that accepts file paths via POST /metadata (JSON body with "paths": [list of strings]), returns metadata for each path (size_bytes, extension, modified_time, is_directory). Handle non-existent paths gracefully with error field. Support GET /recent to return the 10 most recently queried file paths.
