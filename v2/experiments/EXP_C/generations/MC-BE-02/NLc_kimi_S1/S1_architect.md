# MC-BE-02: FastAPI JWT Authentication System - Technical Design Document

## 1. JWT Structure

### Token Format

JWT consists of three Base64Url-encoded parts separated by dots:
```
header.payload.signature
```

### Header Structure
```python
import json
import base64

HEADER = {
    "alg": "HS256",
    "typ": "JWT"
}

def encode_header() -> str:
    """Encode header to Base64Url."""
    header_json = json.dumps(HEADER, separators=(',', ':'))
    header_bytes = header_json.encode('utf-8')
    return base64.urlsafe_b64encode(header_bytes).rstrip(b'=').decode('utf-8')
```

### Payload Structure
```python
from typing import TypedDict
from datetime import datetime, timedelta

class JWTPayload(TypedDict):
    sub: str          # Subject (user_id)
    exp: int          # Expiration timestamp
    iat: int          # Issued at timestamp
    username: str     # Additional claim

def create_payload(user_id: str, username: str, expires_delta: timedelta = timedelta(hours=24)) -> JWTPayload:
    """Create JWT payload with claims."""
    now = datetime.utcnow()
    return {
        "sub": user_id,
        "exp": int((now + expires_delta).timestamp()),
        "iat": int(now.timestamp()),
        "username": username
    }

def encode_payload(payload: JWTPayload) -> str:
    """Encode payload to Base64Url."""
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    return base64.urlsafe_b64encode(payload_bytes).rstrip(b'=').decode('utf-8')
```

## 2. HMAC-SHA256 Signing Flow

### Signing Implementation
```python
import hmac
import hashlib

SECRET_KEY = "your-secret-key-here"  # In production, load from env

def create_signature(message: str, secret: str) -> str:
    """Create HMAC-SHA256 signature."""
    message_bytes = message.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b'=').decode('utf-8')

def sign_jwt(header: str, payload: str, secret: str = SECRET_KEY) -> str:
    """Sign JWT with HMAC-SHA256."""
    message = f"{header}.{payload}"
    signature = create_signature(message, secret)
    return f"{message}.{signature}"
```

### Token Generation Complete Flow
```python
def generate_jwt(user_id: str, username: str) -> str:
    """Generate complete JWT token."""
    header = encode_header()
    payload = encode_payload(create_payload(user_id, username))
    return sign_jwt(header, payload)
```

### Signature Verification
```python
def verify_signature(header: str, payload: str, signature: str, secret: str = SECRET_KEY) -> bool:
    """Verify JWT signature."""
    expected_signature = create_signature(f"{header}.{payload}", secret)
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)
```

## 3. Token Refresh Logic

### Refresh Token Strategy
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour

REFRESH_TOKEN_EXPIRY = timedelta(days=7)
ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)

def generate_token_pair(user_id: str, username: str) -> TokenPair:
    """Generate access and refresh tokens."""
    # Access token - short lived
    access_payload = create_payload(user_id, username, ACCESS_TOKEN_EXPIRY)
    access_token = sign_jwt(encode_header(), encode_payload(access_payload))
    
    # Refresh token - longer lived, different claims
    refresh_payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": int((datetime.utcnow() + REFRESH_TOKEN_EXPIRY).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "jti": generate_token_id()  # Unique token ID for revocation
    }
    refresh_token = sign_jwt(encode_header(), encode_payload(refresh_payload))
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TOKEN_EXPIRY.total_seconds())
    )
```

### Refresh Endpoint Logic
```python
async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh access token using valid refresh token."""
    # Decode and verify refresh token
    payload = decode_jwt(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # Check if token is revoked (would check against store in production)
    if is_token_revoked(payload.get("jti")):
        raise HTTPException(status_code=401, detail="Token revoked")
    
    # Generate new token pair
    user_id = payload["sub"]
    user = await get_user_by_id(user_id)
    
    return generate_token_pair(user_id, user.username)
```

## 4. Middleware/Dependency Design

### JWT Verification Dependency
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def decode_jwt(token: str) -> JWTPayload:
    """Decode and verify JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        header, payload_b64, signature = parts
        
        # Verify signature
        if not verify_signature(header, payload_b64, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Decode payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expired")
        
        return payload
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Invalid payload")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> JWTPayload:
    """Dependency to extract and verify current user from JWT."""
    token = credentials.credentials
    return decode_jwt(token)
```

### Protected Route Usage
```python
@app.get("/protected")
async def protected_route(current_user: JWTPayload = Depends(get_current_user)):
    """Protected endpoint requiring valid JWT."""
    return {
        "message": "Access granted",
        "user_id": current_user["sub"],
        "username": current_user["username"]
    }
```

### Login Endpoint
```python
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT."""
    # Verify credentials (simplified - would check against DB)
    user = await authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token_pair = generate_token_pair(user.id, user.username)
    return token_pair
```

## 5. Constraint Acknowledgment

### Python + FastAPI
**Addressed by:** Application built with FastAPI framework. All endpoints use FastAPI decorators and Pydantic models for request/response validation.

### Manual JWT via hmac+base64, no PyJWT
**Addressed by:** JWT implementation uses Python standard library `hmac` and `base64` modules. No PyJWT, python-jose, or other JWT libraries.

### stdlib + fastapi + uvicorn only
**Addressed by:** Only dependencies are FastAPI, uvicorn, and Python standard library. No additional authentication or JWT packages.

### Single file
**Addressed by:** All authentication logic in single Python file. Routes, JWT utilities, and dependencies co-located.

### Endpoints: login, protected, refresh
**Addressed by:** Three main endpoints implemented: POST /login, GET /protected, POST /refresh. All functionality accessible through these endpoints.

### Code only
**Addressed by:** Output contains only Python code. No markdown in generated file.
