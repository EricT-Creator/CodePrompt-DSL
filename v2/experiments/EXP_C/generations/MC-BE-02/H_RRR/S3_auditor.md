# S3 Auditor — MC-BE-02 (H × RRR)

## Constraint Review
- C1 [L]Python [F]FastAPI: **PASS** — Python with `from fastapi import FastAPI, HTTPException, Request, Depends`; app created as `app = FastAPI(title="JWT Auth API")`
- C2 [!D]NO_JWT_LIB [AUTH]MANUAL_JWT: **PASS** — No JWT library imported (no `pyjwt`, `python-jose`, etc.); JWT manually implemented via `create_jwt()` and `verify_jwt()` using `base64`, `hmac`, `hashlib`, and `json` from stdlib
- C3 [D]STDLIB+FASTAPI: **PASS** — Imports only stdlib (`base64`, `hashlib`, `hmac`, `json`, `time`, `dataclasses`, `typing`) and FastAPI/Pydantic; no other third-party libraries
- C4 [O]SINGLE_FILE: **PASS** — All code (JWT logic, auth dependencies, routes, models) contained in a single file
- C5 [API]LOGIN_PROTECTED_REFRESH: **PASS** — Three endpoints implemented: `POST /login` (credentials → tokens), `GET /protected` (requires access token via `Depends(require_auth)`), `POST /refresh` (requires refresh token via `Depends(require_refresh_token)` → new token pair)
- C6 [OUT]CODE_ONLY: **PASS** — Output is pure code with no prose; comments are minimal and code-relevant

## Functionality Assessment (0-5)
Score: 5 — Complete JWT authentication system with manual HMAC-SHA256 signing/verification, base64url encoding/decoding, access and refresh tokens with expiry, token type validation, constant-time password comparison, Bearer token extraction from Authorization header, and proper error handling (401 for invalid/expired tokens). Production-quality implementation.

## Corrected Code
No correction needed.
