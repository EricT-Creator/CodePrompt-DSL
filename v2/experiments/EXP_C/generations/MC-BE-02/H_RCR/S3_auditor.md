## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — File is Python; uses FastAPI (`from fastapi import FastAPI, Request, HTTPException, Depends`, `app = FastAPI()`).
- C2 [!D]NO_JWT_LIB [AUTH]MANUAL_JWT: PASS — No JWT library imported (no `PyJWT`, `python-jose` etc.); JWT encoding/decoding is manually implemented in `JWTUtil` class using `base64`, `hmac`, `hashlib`, `json` from stdlib.
- C3 [D]STDLIB+FASTAPI: PASS — Only imports from Python stdlib (`base64`, `hashlib`, `hmac`, `json`, `time`, `dataclasses`, `typing`) and FastAPI/Pydantic. No third-party libraries.
- C4 [O]SINGLE_FILE: PASS — All code (JWT util, user store, auth middleware, endpoints) is in a single file.
- C5 [API]LOGIN_PROTECTED_REFRESH: PASS — Three endpoints implemented: `POST /login` returns access+refresh tokens; `GET /protected` requires Bearer access token via `Depends(require_auth)`; `POST /refresh` accepts refresh token via `Depends(require_refresh_token)` and returns new token pair.
- C6 [OUT]CODE_ONLY: PASS — Output is code only.

## Functionality Assessment (0-5)
Score: 5 — Complete manual JWT auth system with: base64url encoding/decoding, HMAC-SHA256 signing/verification, token type enforcement (access vs refresh), expiry checks, Bearer header extraction, password hashing (SHA256), hardcoded user store, and all three required API endpoints. Secure comparison via `hmac.compare_digest`.

## Corrected Code
No correction needed.
