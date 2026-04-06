## Constraint Review
- C1 (Python + FastAPI): PASS — Code uses `from fastapi import Depends, FastAPI, HTTPException, status` and defines `app = FastAPI(title="JWT Auth Service")`.
- C2 (Manual JWT, no PyJWT): PASS — JWT signing and verification are implemented manually using `hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256)` for HMAC-SHA256 and `base64.urlsafe_b64encode`/`b64url_decode` for base64url encoding. No PyJWT or python-jose is imported.
- C3 (stdlib + fastapi only): PASS — Only imports from Python standard library (`base64`, `hashlib`, `hmac`, `json`, `time`, `uuid`, `datetime`, `typing`), `fastapi`, `pydantic` (bundled with fastapi), and `uvicorn`.
- C4 (Single file): PASS — All code is contained in a single Python file.
- C5 (login/protected/refresh endpoints): PASS — Three required endpoints are implemented: `@app.post("/login")`, `@app.get("/protected")`, and `@app.post("/refresh")`.
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT authentication system with manual HMAC-SHA256 signing/verification, base64url encoding, access token (15min TTL) and refresh token (7-day TTL) with JTI tracking, mock user database with role-based claims, token type validation, refresh token revocation support, and proper HTTP 401 responses with WWW-Authenticate headers.

## Corrected Code
No correction needed.
