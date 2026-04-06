## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException, Depends` and defines `app = FastAPI(title="JWT Authentication System")`.
- C2 (Manual JWT, no PyJWT): PASS — JWT created manually via `hmac.new()` + `hashlib.sha256` + `base64.urlsafe_b64encode()` + `json.dumps()` in `create_jwt()`; verification via `hmac.compare_digest()` in `verify_jwt()`; no PyJWT or jose imported.
- C3 (stdlib + fastapi only): PASS — Imports only stdlib modules (hmac, hashlib, base64, json, time, typing) plus fastapi and pydantic; no external packages.
- C4 (Single file): PASS — All code (JWT helpers, user store, endpoints, auth dependency) in one file.
- C5 (login/protected/refresh endpoints): PASS — `@app.post("/login")` returns access+refresh tokens; `@app.get("/protected")` requires Bearer token via `Depends(get_current_user)`; `@app.post("/refresh")` rotates tokens with revocation.
- C6 (Code only): PASS — File contains only code with minimal section comments.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with: manual HS256 JWT creation/verification, base64url encoding with proper padding, access token (15min) and refresh token (7 days), token type validation, expiration checking, refresh token rotation with revocation set, HTTPBearer security dependency, proper error responses (401), and clean separation of concerns.

## Corrected Code
No correction needed.
