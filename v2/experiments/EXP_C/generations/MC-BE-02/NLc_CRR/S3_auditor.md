## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException, Depends, status` with Python standard library modules.
- C2 (Manual JWT, no PyJWT): PASS — JWT implementation is entirely hand-written using `hmac.new()` with `hashlib.sha256`, `base64.urlsafe_b64encode/decode`, and `json.dumps/loads`; no `jwt` or `PyJWT` imported.
- C3 (stdlib + fastapi only): PASS — Imports: `json`, `hmac`, `hashlib`, `base64`, `uuid`, `time`, `datetime`, `dataclasses`, `typing` (all stdlib) + `fastapi`, `pydantic` (FastAPI dependency). No external packages.
- C4 (Single file): PASS — All code in one file with `if __name__ == "__main__": uvicorn.run(...)` at the end.
- C5 (login/protected/refresh endpoints): PASS — `@app.post("/login")` for authentication, `@app.get("/protected")` with `Depends(get_current_user)` for protected access, `@app.post("/refresh")` for token refresh with revocation.
- C6 (Code only): PASS — No prose or explanation; the file contains only executable code.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT auth system with manual HS256 implementation (header/payload/signature), access + refresh token pair generation, token expiry validation, refresh token rotation with JTI-based revocation, constant-time signature comparison via `hmac.compare_digest`, mock user store, HTTPBearer security scheme, and proper error handling with 401 status codes. All core features fully implemented.

## Corrected Code
No correction needed.
