# MC-BE-02: JWT Authentication System - Technical Design

## Overview

This document outlines the technical design for a FastAPI JWT authentication system using only Python standard library HMAC-SHA256 for token signing and verification.

## 1. JWT Structure

### Token Format

```
JWT = base64url(header) + "." + base64url(payload) + "." + base64url(signature)
```

### Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload (Claims)

```python
class JWTPayload(BaseModel):
    sub: str          # Subject (user_id)
    exp: int          # Expiration timestamp (Unix epoch)
    iat: int          # Issued at timestamp
    jti: str          # JWT ID (unique token identifier)
    
    # Optional custom claims
    username: str
    roles: List[str]
```

### Signature

```
signature = HMAC-SHA256(
    key = SECRET_KEY,
    message = base64url(header) + "." + base64url(payload)
)
```

## 2. HMAC-SHA256 Signing Flow

### Implementation (Standard Library Only)

```python
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta

def base64url_encode(data: bytes) -> str:
    """Base64URL encoding (no padding, - instead of +, _ instead of /)."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def base64url_decode(data: str) -> bytes:
    """Base64URL decoding (add padding if needed)."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)

def sign_jwt(payload: dict, secret_key: str) -> str:
    """Sign a JWT using HMAC-SHA256."""
    # Create header
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    
    # Create signing input
    signing_input = f"{header_b64}.{payload_b64}"
    
    # Generate signature
    signature = hmac.new(
        secret_key.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    
    # Return complete JWT
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_jwt(token: str, secret_key: str) -> dict:
    """Verify a JWT signature and return payload."""
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    
    header_b64, payload_b64, signature_b64 = parts
    
    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = hmac.new(
        secret_key.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    expected_signature_b64 = base64url_encode(expected_signature)
    
    if not hmac.compare_digest(signature_b64, expected_signature_b64):
        raise ValueError("Invalid signature")
    
    # Decode and return payload
    payload_json = base64url_decode(payload_b64)
    return json.loads(payload_json)
```

## 3. Token Refresh Logic

### Refresh Token Flow

```
User Login:
  ├─ Validate credentials
  ├─ Generate access_token (15 min expiry)
  ├─ Generate refresh_token (7 day expiry)
  └─ Return both tokens

Access Protected Resource:
  ├─ Extract access_token from Authorization header
  ├─ Verify signature
  ├─ Check expiration
  ├─ If expired: Return 401
  └─ If valid: Process request

Refresh Token:
  ├─ Receive refresh_token in POST /refresh
  ├─ Verify refresh_token signature
  ├─ Check refresh_token expiration
  ├─ Generate new access_token
  └─ Return new access_token
```

### Token Storage

```python
class TokenStore:
    """In-memory token storage with refresh token tracking."""
    
    def __init__(self):
        self._refresh_tokens: Dict[str, dict] = {}  # jti -> token_data
        self._revoked_tokens: Set[str] = set()      # Set of revoked jtis
    
    def store_refresh_token(self, jti: str, user_id: str, expires_at: datetime) -> None:
        self._refresh_tokens[jti] = {
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
    
    def is_refresh_token_valid(self, jti: str) -> bool:
        if jti in self._revoked_tokens:
            return False
        token_data = self._refresh_tokens.get(jti)
        if not token_data:
            return False
        return datetime.utcnow() < token_data["expires_at"]
    
    def revoke_refresh_token(self, jti: str) -> None:
        self._revoked_tokens.add(jti)
```

## 4. Middleware/Dependency Design

### FastAPI Dependencies

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    secret_key: str = Depends(get_secret_key)
) -> User:
    """Dependency to extract and verify JWT from Authorization header."""
    token = credentials.credentials
    
    try:
        payload = verify_jwt(token, secret_key)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    
    # Check expiration
    exp = payload.get("exp")
    if exp and datetime.utcnow().timestamp() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return User(
        id=payload["sub"],
        username=payload["username"],
        roles=payload.get("roles", [])
    )

# Protected endpoint usage
@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}"}
```

### Endpoint Implementations

```python
@app.post("/login")
async def login(credentials: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    # Verify credentials against user store
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@app.get("/protected")
async def protected(user: User = Depends(get_current_user)) -> dict:
    """Return user data for valid JWT."""
    return {
        "user_id": user.id,
        "username": user.username,
        "roles": user.roles
    }

@app.post("/refresh")
async def refresh(request: RefreshRequest) -> TokenResponse:
    """Refresh access token using valid refresh token."""
    # Verify refresh token
    payload = verify_jwt(request.refresh_token, SECRET_KEY)
    jti = payload.get("jti")
    
    if not token_store.is_refresh_token_valid(jti):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Get user and generate new access token
    user = get_user_by_id(payload["sub"])
    access_token = create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Keep same refresh token
        token_type="bearer"
    )
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python + FastAPI** | Use FastAPI with Pydantic models for type validation |
| **No JWT libraries** | Implement JWT signing/verification using `hmac` and `base64` from standard library |
| **Standard library + FastAPI + uvicorn only** | No PyJWT, python-jose, or other JWT dependencies |
| **Single Python file** | All code (models, JWT logic, endpoints, middleware) in one file |
| **Required endpoints** | POST /login, GET /protected, POST /refresh all implemented |
| **Output code only** | Design structured for direct implementation |

## Summary

This design implements a complete JWT authentication system using only Python's standard library for cryptographic operations. HMAC-SHA256 provides secure token signing, while base64url encoding ensures JWT specification compliance. The refresh token mechanism enables long-lived sessions without compromising security. FastAPI dependencies provide clean integration with protected endpoints.
