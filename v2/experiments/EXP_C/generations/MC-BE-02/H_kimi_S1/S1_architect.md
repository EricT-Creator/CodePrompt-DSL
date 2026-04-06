# MC-BE-02: JWT Auth Middleware — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. JWT Structure

### 1.1 Token Format

```
header.payload.signature
```

### 1.2 Header

```json
{
    "alg": "HS256",
    "typ": "JWT"
}
```

### 1.3 Payload (Claims)

```json
{
    "sub": "user-id",
    "username": "john_doe",
    "iat": 1711965600,
    "exp": 1711969200,
    "jti": "unique-token-id"
}
```

### 1.4 Signature

```python
signature = HMAC-SHA256(
    base64url(header) + "." + base64url(payload),
    secret_key
)
```

---

## 2. HMAC-SHA256 Signing Flow

### 2.1 Encoding Functions

```python
import base64
import hashlib
import hmac
import json

def base64url_encode(data: bytes) -> str:
    """Base64URL encoding without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def base64url_decode(data: str) -> bytes:
    """Base64URL decoding with padding restoration"""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)
```

### 2.2 Signing Process

```python
def sign_token(header: dict, payload: dict, secret: str) -> str:
    # Encode header
    header_json = json.dumps(header, separators=(',', ':'))
    header_b64 = base64url_encode(header_json.encode())
    
    # Encode payload
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64url_encode(payload_json.encode())
    
    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"
```

### 2.3 Verification Process

```python
def verify_token(token: str, secret: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    
    header_b64, payload_b64, signature_b64 = parts
    
    # Verify signature
    message = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = base64url_encode(expected_sig)
    
    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise ValueError("Invalid signature")
    
    # Decode payload
    payload_json = base64url_decode(payload_b64)
    payload = json.loads(payload_json)
    
    # Check expiry
    if payload.get('exp', 0) < time.time():
        raise ValueError("Token expired")
    
    return payload
```

---

## 3. Token Refresh Logic

### 3.1 Refresh Strategy

- Access tokens: Short-lived (15 minutes)
- Refresh tokens: Long-lived (7 days)
- Refresh endpoint exchanges valid refresh token for new access token

### 3.2 Refresh Flow

```python
@app.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = verify_token(refresh_token, REFRESH_SECRET)
        
        # Issue new access token
        new_access_token = create_access_token(
            user_id=payload['sub'],
            username=payload['username']
        )
        
        return {"access_token": new_access_token}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
```

---

## 4. Middleware/Dependency Design

### 4.1 FastAPI Dependency

```python
from fastapi import Depends, HTTPException, Header
from typing import Annotated

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization[7:]  # Remove "Bearer "
    
    try:
        payload = verify_token(token, SECRET_KEY)
        return User(id=payload['sub'], username=payload['username'])
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Usage
@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}"}
```

### 4.2 Route Protection

| Route | Protection |
|-------|-----------|
| POST /login | Public |
| GET /protected | JWT required |
| POST /refresh | Valid refresh token required |

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]Python` | Python 3.10+ implementation |
| `[F]FastAPI` | FastAPI framework |
| `[!D]NO_JWT_LIB` | No PyJWT; manual HMAC-SHA256 implementation |
| `[AUTH]MANUAL_JWT` | Hand-written encoding/decoding/verification |
| `[D]STDLIB+FASTAPI` | hashlib, hmac, base64 from stdlib only |
| `[O]SINGLE_FILE` | All code in single file |
| `[API]LOGIN_PROTECTED_REFRESH` | Three endpoints as specified |
| `[OUT]CODE_ONLY` | Output will be code only |

---

## 6. File Structure

```
MC-BE-02/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── main.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
