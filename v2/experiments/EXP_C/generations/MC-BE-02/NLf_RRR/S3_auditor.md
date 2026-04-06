## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException, Depends, Header` and defines `app = FastAPI(...)` with route decorators.
- C2 (Manual JWT, no PyJWT): PASS — JWT is implemented manually using `hmac.new(..., hashlib.sha256)` for signing and `base64.urlsafe_b64encode/decode` for encoding. Functions `create_jwt()` and `verify_jwt()` handle token creation and verification. No PyJWT, python-jose, or any JWT library imported.
- C3 (stdlib + fastapi only): PASS — Imports only `base64`, `hashlib`, `hmac`, `json`, `time`, `uuid`, `typing` from stdlib, plus `fastapi` and `pydantic`. No other third-party packages.
- C4 (Single file): PASS — All code is in a single Python file.
- C5 (login/protected/refresh endpoints): PASS — Implements `POST /login` (authenticates user, returns tokens), `GET /protected` (requires access token via dependency injection), and `POST /refresh` (rotates refresh token with JTI revocation).
- C6 (Code only): PASS — File contains only code with structural section markers, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Implements a complete JWT authentication system with: manual HMAC-SHA256 JWT signing/verification, base64url encoding with proper padding, access + refresh token pair with configurable expiry (15min / 7 days), token type validation (access vs refresh), JTI-based token revocation on refresh, timing-safe password comparison using `hmac.compare_digest`, in-memory user store with SHA-256 hashed passwords, and proper error handling with 401 responses.

## Corrected Code
No correction needed.
