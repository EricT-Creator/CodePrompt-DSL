# Technical Design Document: JWT Auth Middleware

**Task**: MC-BE-02  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]Python [F]FastAPI [!D]NO_JWT_LIB [AUTH]MANUAL_JWT [D]STDLIB+FASTAPI [O]SINGLE_FILE [API]LOGIN_PROTECTED_REFRESH [OUT]CODE_ONLY`

---

## 1. JWT Structure (header.payload.signature)

### Standard JWT Three-Part Structure

```
<base64url(header)>.<base64url(payload)>.<base64url(signature)>
```

### Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

Always `HS256` — no algorithm negotiation (prevents `alg:none` attack).

### Payload (Claims)

```json
{
  "sub": "user_id",
  "username": "john",
  "iat": 1711900000,        // issued-at timestamp
  "exp": 1711903600,        // expiry timestamp (iat + 1 hour for access token)
  "type": "access"          // "access" or "refresh"
}
```

- **Access token**: Short-lived (1 hour).
- **Refresh token**: Longer-lived (7 days). Contains `"type": "refresh"`.

### Signature

```
HMAC-SHA256(
  key = SECRET_KEY,
  message = base64url(header) + "." + base64url(payload)
)
```

---

## 2. HMAC-SHA256 Signing Flow

### Encoding Steps

1. **Serialize** header dict to JSON bytes (compact, no whitespace).
2. **Base64url encode** header → `header_b64`.
3. **Serialize** payload dict to JSON bytes.
4. **Base64url encode** payload → `payload_b64`.
5. **Concatenate** signing input: `f"{header_b64}.{payload_b64}"`.
6. **Compute HMAC-SHA256**: `hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()`.
7. **Base64url encode** signature → `sig_b64`.
8. **Assemble token**: `f"{header_b64}.{payload_b64}.{sig_b64}"`.

### Base64url Details

- Use `base64.urlsafe_b64encode()`.
- Strip trailing `=` padding on encode.
- Re-add padding on decode: `padded = s + "=" * (4 - len(s) % 4) % 4`.

### Verification Steps

1. Split token by `.` → must yield exactly 3 parts.
2. Recompute signature from parts[0] + "." + parts[1] using the secret key.
3. **Constant-time comparison** via `hmac.compare_digest()` to prevent timing attacks.
4. Decode payload, check `exp` against `time.time()`.
5. If expired → raise 401 with "Token expired" message.
6. If signature mismatch → raise 401 with "Invalid token" message.

---

## 3. Token Refresh Logic

### Flow

```
Client has expired access token + valid refresh token
  → POST /refresh with refresh token in Authorization header
    → Server verifies refresh token (signature + expiry + type="refresh")
    → If valid: issue new access token + new refresh token
    → If invalid: return 401
```

### Refresh Token Rotation

Each refresh generates a **new** refresh token, invalidating the old one conceptually (since we have no persistent store, expiry is the only invalidation mechanism). In a production system, a token blacklist would be added.

### Token Extraction

Tokens are extracted from the `Authorization: Bearer <token>` header. A helper function `extract_token(request)` handles:
- Missing header → 401
- Malformed header (not "Bearer <token>") → 401
- Returns the raw token string for verification.

---

## 4. Middleware / Dependency Design

### FastAPI Dependency Injection

Instead of traditional middleware, use FastAPI's `Depends()` pattern for cleaner per-route auth:

```python
async def require_auth(request: Request) -> dict:
    token = extract_token(request)
    payload = verify_jwt(token, expected_type="access")
    return payload   # decoded user claims
```

### Route Wiring

| Endpoint | Auth Required | Dependency |
|----------|--------------|------------|
| `POST /login` | No | None — public endpoint |
| `GET /protected` | Yes (access token) | `Depends(require_auth)` |
| `POST /refresh` | Yes (refresh token) | Custom: `Depends(require_refresh_token)` |

### `require_refresh_token` Dependency

Same as `require_auth` but validates `type == "refresh"` in the payload. If the token is an access token used on the refresh endpoint, it returns 401.

### User Store (Mock)

An in-memory `dict[str, dict]` stores mock users:

```python
USERS = {
    "john": {"password_hash": "hashed_pw", "user_id": "u001"},
    "jane": {"password_hash": "hashed_pw", "user_id": "u002"},
}
```

Password verification uses `hashlib.sha256` (sufficient for mock; not bcrypt since no external libs).

### Error Responses

All auth failures return:
```json
{ "detail": "..." }
```
with HTTP 401 status code and appropriate error message.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: Python | `[L]Python` | Entire implementation in Python 3.10+. |
| Framework: FastAPI | `[F]FastAPI` | API endpoints, dependency injection, and Pydantic models all via FastAPI. |
| No JWT library | `[!D]NO_JWT_LIB` | No PyJWT, python-jose, or any JWT library. JWT creation and verification implemented from scratch using `hmac`, `hashlib`, `base64`, `json`, `time`. |
| Manual JWT implementation | `[AUTH]MANUAL_JWT` | Full manual implementation: base64url encoding, HMAC-SHA256 signing, token assembly, signature verification, expiry checking. |
| Dependencies: stdlib + FastAPI | `[D]STDLIB+FASTAPI` | Only stdlib modules (`hmac`, `hashlib`, `base64`, `json`, `time`, `dataclasses`) and FastAPI/Pydantic. |
| Single file | `[O]SINGLE_FILE` | Entire application (models, auth logic, routes, user store) in one `.py` file. |
| API: login + protected + refresh | `[API]LOGIN_PROTECTED_REFRESH` | Three endpoints: `POST /login`, `GET /protected`, `POST /refresh`. |
| Code only output | `[OUT]CODE_ONLY` | Final S2 deliverable will be pure code. |
