## Constraint Review
- C1 (Python + FastAPI): PASS — `from fastapi import Depends, FastAPI, HTTPException, status`; `app = FastAPI(title="JWT Authentication System")`.
- C2 (Manual JWT, no PyJWT): PASS — JWT signing via `hmac.new(secret_key.encode("utf-8"), ..., hashlib.sha256)` with `base64url_encode/decode`. No PyJWT, python-jose, or any JWT library imported.
- C3 (stdlib + fastapi only): PASS — Imports are `base64`, `hashlib`, `hmac`, `json`, `uuid`, `datetime`, `typing` (all stdlib) plus `fastapi` and `pydantic` (bundled with fastapi).
- C4 (Single file): PASS — All code in one file: models, JWT implementation, token store, auth helpers, FastAPI app, and endpoints.
- C5 (login/protected/refresh endpoints): PASS — `@app.post("/login")`, `@app.get("/protected")`, `@app.post("/refresh")` all present and functional.
- C6 (Code only): PASS — No explanatory prose; file is pure code.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with: manual HS256 signing/verification, base64url encoding with proper padding, access + refresh token pair, token type checking, expiration enforcement, refresh token store with revocation support, 3 demo users, HTTPBearer dependency injection, and proper error handling with WWW-Authenticate headers.

## Corrected Code
No correction needed.
