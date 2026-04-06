[L]Python [F]FastAPI [!D]NO_JWT_LIB [AUTH]MANUAL_JWT [D]STDLIB+FASTAPI [O]SINGLE_FILE [API]LOGIN_PROTECTED_REFRESH [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. JWT structure (header.payload.signature)
2. HMAC-SHA256 signing flow
3. Token refresh logic
4. Middleware/dependency design
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI JWT authentication system: POST /login to sign a JWT, GET /protected to verify JWT and return user data (401 on invalid), POST /refresh to refresh a token. JWT must use HMAC-SHA256 signing with correct base64url encoding and expiry detection.
