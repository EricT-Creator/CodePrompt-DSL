You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. stdlib + fastapi + uvicorn only. ALL route handlers must use sync `def`, NOT `async def`. DO NOT use pathlib — use os.path for all file operations. Single file. Code only.

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
