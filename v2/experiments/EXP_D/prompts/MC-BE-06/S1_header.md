[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!ASYNC]SYNC_DEF_ONLY [!PATH]OS_PATH_ONLY [FILE]SINGLE [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

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
