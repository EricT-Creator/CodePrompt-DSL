You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. Manual JWT via hmac+base64, no PyJWT. stdlib + fastapi + uvicorn only. Single file. Endpoints: login, protected, refresh. Code only.

Include:
1. JWT structure (header.payload.signature)
2. HMAC-SHA256 signing flow
3. Token refresh logic
4. Middleware/dependency design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI JWT authentication system: POST /login to sign a JWT, GET /protected to verify JWT and return user data (401 on invalid), POST /refresh to refresh a token. JWT must use HMAC-SHA256 signing with correct base64url encoding and expiry detection.
