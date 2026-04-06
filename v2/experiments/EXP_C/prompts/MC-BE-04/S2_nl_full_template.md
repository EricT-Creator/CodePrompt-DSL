You are a developer. Implement the technical design below as a single Python file (.py). Follow ALL engineering constraints listed below strictly. Output code only, no explanation.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Implement rate limiting using the Token Bucket algorithm. Do not use simple counter-based or fixed window approaches.
3. Only use Python standard library and fastapi. Do not use Redis, memcached, or any external storage.
4. Deliver everything in a single Python file.
5. Return HTTP 429 with Retry-After header when rate exceeded. Support an IP whitelist that bypasses rate limiting.
6. Output code only, no explanation text.

Technical Design:
---
{S1_OUTPUT}
---
