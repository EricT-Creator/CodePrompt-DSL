## Constraint Review
- C1 (Python + FastAPI): PASS — File uses Python with `from fastapi import FastAPI, HTTPException, Depends` and defines a FastAPI application instance.
- C2 (Manual JWT, no PyJWT): PASS — JWT creation and verification implemented manually using `hmac.new()` + `hashlib.sha256` for HMAC-SHA256 signatures and `base64.urlsafe_b64encode/decode` for encoding; no PyJWT, python-jose, or other JWT libraries imported.
- C3 (stdlib + fastapi only): PASS — All imports are from Python stdlib (`base64`, `hashlib`, `hmac`, `json`, `time`, `uuid`, `dataclasses`, `datetime`, `typing`) or FastAPI/Pydantic (`fastapi`, `pydantic`); `uvicorn` used only in `__main__` block.
- C4 (Single file): PASS — All code (JWT utilities, user store, FastAPI routes, dependencies) defined in a single file.
- C5 (login/protected/refresh endpoints): PASS — Three required endpoints present: `POST /login` (authenticates and returns tokens), `GET /protected` (requires Bearer token via `get_current_user` dependency), `POST /refresh` (accepts refresh token and issues new token pair).
- C6 (Code only): PASS — File contains only executable Python code with no embedded documentation or non-code content.

## Functionality Assessment (0-5)
Score: 5 — Complete JWT authentication system with manual token creation/verification, separate access and refresh tokens with different expiry times, proper HMAC signature verification using `hmac.compare_digest` (timing-safe comparison), token type enforcement (access vs refresh), user store with authentication, HTTPBearer security scheme integration, and demo endpoints for user management. The implementation correctly handles base64url padding, expiration checking, and error propagation.

## Corrected Code
No correction needed.
