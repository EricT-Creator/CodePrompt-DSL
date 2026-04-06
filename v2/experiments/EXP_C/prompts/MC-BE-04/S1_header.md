[L]Python [F]FastAPI [ALGO]TOKEN_BUCKET [!A]NO_COUNTER [D]STDLIB+FASTAPI [!D]NO_REDIS [O]SINGLE_FILE [RESP]429_RETRY_AFTER [WL]IP [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. Token Bucket algorithm details
2. Per-IP bucket management
3. Middleware integration
4. Retry-After calculation
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI Token Bucket rate limiter middleware: configurable rate/burst per IP, return HTTP 429 with Retry-After header when rate exceeded, and support an IP whitelist that bypasses rate limiting.
