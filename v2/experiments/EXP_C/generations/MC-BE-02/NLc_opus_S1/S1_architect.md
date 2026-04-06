# Technical Design Document — JWT Authentication System

## 1. Overview

A FastAPI authentication service implementing JWT (JSON Web Token) from scratch using HMAC-SHA256 signing. Provides login, token verification, and token refresh endpoints — all without third-party JWT libraries.

## 2. JWT Structure

A JWT consists of three Base64URL-encoded segments separated by dots:

```
header.payload.signature
```

### Header
```json
{ "alg": "HS256", "typ": "JWT" }
```
Always static for this implementation.

### Payload
```json
{
  "sub": "<username>",
  "iat": <issued_at_unix>,
  "exp": <expiry_unix>,
  "type": "access" | "refresh"
}
```

- `sub`: the user identity (username string).
- `iat`: Unix timestamp of token creation.
- `exp`: Unix timestamp of expiry. Access tokens: 15 minutes. Refresh tokens: 7 days.
- `type`: distinguishes access tokens from refresh tokens to prevent cross-use.

### Signature
```
HMAC-SHA256(
  key = SECRET_KEY,
  message = base64url(header) + "." + base64url(payload)
)
```
The signature is then Base64URL-encoded and appended as the third segment.

## 3. HMAC-SHA256 Signing Flow

### Encoding Steps
1. JSON-serialize the header dict → UTF-8 bytes → Base64URL encode (no padding).
2. JSON-serialize the payload dict → UTF-8 bytes → Base64URL encode (no padding).
3. Concatenate: `encoded_header + "." + encoded_payload` → this is the signing input.
4. Compute `hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()`.
5. Base64URL-encode the digest (no padding).
6. Final token: `encoded_header.encoded_payload.encoded_signature`.

### Base64URL Specifics
- Use `base64.urlsafe_b64encode`, then strip trailing `=` padding characters.
- For decoding, re-add padding: `s += '=' * (4 - len(s) % 4)` before `base64.urlsafe_b64decode`.

### Verification Steps
1. Split the token on `.` into three parts.
2. Recompute the signature from parts[0] and parts[1] using the secret key.
3. Compare with parts[2] using `hmac.compare_digest` (timing-safe).
4. Decode the payload and check `exp` against `time.time()`.
5. If signature mismatch or expired → reject.

## 4. Token Refresh Logic

### Two-Token Pattern
- **Access token** (short-lived, 15 min): used in `Authorization: Bearer <token>` for protected endpoints.
- **Refresh token** (long-lived, 7 days): used only at `POST /refresh` to obtain a new access token.

### Refresh Flow
1. Client sends `POST /refresh` with `{ "refresh_token": "<token>" }`.
2. Server verifies the refresh token (signature + expiry + `type == "refresh"`).
3. If valid: issue a new access token (and optionally a new refresh token for rotation).
4. If invalid or expired: return 401.

### Refresh Token Rotation (optional enhancement)
Each refresh issues both a new access and a new refresh token. The old refresh token is invalidated by tracking issued refresh token IDs in a `set`. This limits the window for stolen refresh tokens.

## 5. API Endpoint Design

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| `POST` | `/login` | None | `{ "username": str, "password": str }` | `{ "access_token": str, "refresh_token": str, "token_type": "bearer" }` |
| `GET` | `/protected` | Bearer access token | — | `{ "user": str, "message": str }` or 401 |
| `POST` | `/refresh` | None (token in body) | `{ "refresh_token": str }` | `{ "access_token": str, "token_type": "bearer" }` or 401 |

### User Store
- A simple in-memory dict: `users = { "admin": "password123", "user1": "pass456" }`.
- Passwords stored in plain text (acceptable for this demo scope; a real system would hash them).

## 6. Middleware / Dependency Design

### FastAPI Dependency: `get_current_user`
- Extracts the `Authorization` header.
- Strips the `Bearer ` prefix.
- Calls the verification function.
- If valid, returns the decoded payload (specifically `sub`).
- If invalid (bad signature, expired, wrong type), raises `HTTPException(401)`.

### Integration
```python
@app.get("/protected")
async def protected(user: str = Depends(get_current_user)):
    return {"user": user, "message": "Access granted"}
```

No global middleware is needed; the dependency injection pattern keeps auth concerns localized to endpoints that require it.

## 7. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python + FastAPI** | Application is a FastAPI app with standard decorators and Pydantic models. |
| 2 | **Manual JWT via hmac+base64, no PyJWT** | JWT creation and verification use only `hmac`, `hashlib`, `base64`, `json`, and `time` from Python stdlib. No `PyJWT`, `python-jose`, or `authlib`. |
| 3 | **stdlib + fastapi + uvicorn only** | Imports are limited to Python standard library modules plus `fastapi` and `uvicorn`. |
| 4 | **Single file** | All logic — endpoint handlers, JWT functions, user store, dependency — resides in a single `.py` file. |
| 5 | **Endpoints: login, protected, refresh** | Exactly three endpoints are implemented as specified: `POST /login`, `GET /protected`, `POST /refresh`. |
| 6 | **Code only** | The deliverable is pure Python source code. |
