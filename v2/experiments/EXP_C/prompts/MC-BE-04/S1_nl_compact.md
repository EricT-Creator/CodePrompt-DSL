You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. Token Bucket required, no simple counter. stdlib + fastapi only, no Redis. Single file. 429 with Retry-After, IP whitelist. Code only.

Include:
1. Token Bucket algorithm details
2. Per-IP bucket management
3. Middleware integration
4. Retry-After calculation
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI Token Bucket rate limiter middleware: configurable rate/burst per IP, return HTTP 429 with Retry-After header when rate exceeded, and support an IP whitelist that bypasses rate limiting.
