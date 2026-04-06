You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Implement rate limiting using the Token Bucket algorithm. Do not use simple counter-based or fixed window approaches.
3. Only use Python standard library and fastapi. Do not use Redis, memcached, or any external storage.
4. Deliver everything in a single Python file.
5. Return HTTP 429 with Retry-After header when rate exceeded. Support an IP whitelist that bypasses rate limiting.
6. Output code only, no explanation text.

Include:
1. Token Bucket algorithm details
2. Per-IP bucket management
3. Middleware integration
4. Retry-After calculation
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI Token Bucket rate limiter middleware: configurable rate/burst per IP, return HTTP 429 with Retry-After header when rate exceeded, and support an IP whitelist that bypasses rate limiting.
