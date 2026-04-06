# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-BE-02

## Constraint Review
- C1 (Python + FastAPI): PASS — 使用FastAPI框架
- C2 (Manual JWT, no PyJWT): PASS — 使用hmac和base64标准库实现JWT签名和验证，无PyJWT等库
- C3 (stdlib + fastapi only): PASS — 仅使用Python标准库、fastapi和uvicorn
- C4 (Single file): PASS — 所有代码在一个Python文件中
- C5 (login/protected/refresh endpoints): PASS — 提供POST /login、GET /protected、POST /refresh端点
- C6 (Code only): FAIL — 审查报告包含解释文本，而不仅仅是代码

## Functionality Assessment (0-5)
Score: 4 — 实现了一个完整的JWT认证系统，包含登录、受保护端点访问、令牌刷新等功能。使用hmac和base64手动实现JWT签名验证，符合不使用外部JWT库的要求。系统功能完整，但审查报告违反了"只输出代码"的要求。

## Corrected Code
由于C6约束失败（审查报告包含解释文本而非仅代码），以下是修复后的完整.py文件。但请注意，审查报告本身仍需要包含解释，这是一个内在矛盾：

```py
"""JWT Authentication System with FastAPI — manual HMAC-SHA256 JWT."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel


# ── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2026"
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days


# ── User Store ───────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


users_db: dict[str, dict[str, str]] = {
    "admin": {
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "email": "admin@example.com",
    },
    "user": {
        "password_hash": hash_password("user123"),
        "role": "user",
        "email": "user@example.com",
    },
}

refresh_tokens: dict[str, dict[str, Any]] = {}


# ── JWT Implementation ───────────────────────────────────────────────────────


def base64url_encode(data: bytes) -> str:
    """Base64 URL-safe encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def base64url_decode(data: str) -> bytes:
    """Base64 URL-safe decode."""
    padding = 4 - (len(data) % 4)
    data = data + ("=" * padding)
    return base64.urlsafe_b64decode(data)


def sign_jwt(payload: dict[str, Any], secret: str, expire_seconds: int) -> str:
    """Create a JWT token manually."""
    # Add standard claims
    now = int(time.time())
    payload["iat"] = now
    payload["exp"] = now + expire_seconds
    payload["jti"] = str(uuid.uuid4())

    # Encode header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode())

    # Encode payload
    payload_b64 = base64url_encode(json.dumps(payload).encode())

    # Create signature
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(
        secret.encode(), signing_input, hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str, secret: str) -> dict[str, Any] | None:
    """Verify a JWT token manually."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Recreate signature
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_signature = hmac.new(
            secret.encode(), signing_input, hashlib.sha256
        ).digest()
        expected_signature_b64 = base64url_encode(expected_signature)

        # Compare signatures
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None

        # Decode payload
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)

        # Check expiration
        if "exp" in payload and payload["exp"] < time.time():
            return None

        return payload
    except Exception:
        return None


def create_access_token(user_id: str, role: str) -> str:
    """Create an access token."""
    payload = {
        "sub": user_id,
        "role": role,
        "token_type": "access",
    }
    return sign_jwt(payload, SECRET_KEY, ACCESS_TOKEN_EXPIRE)


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token and store it."""
    payload = {
        "sub": user_id,
        "token_type": "refresh",
    }
    token = sign_jwt(payload, SECRET_KEY, REFRESH_TOKEN_EXPIRE)
    
    # Store refresh token
    refresh_tokens[token] = {
        "user_id": user_id,
        "created_at": time.time(),
    }
    
    return token


# ── Pydantic Models ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    user_id: str
    role: str
    email: str


# ── Authentication Dependency ────────────────────────────────────────────────


async def get_current_user(authorization: str = Header(...)) -> dict[str, Any]:
    """Dependency to get current user from JWT."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    payload = verify_jwt(token, SECRET_KEY)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if payload.get("token_type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    return payload


# ── FastAPI App ──────────────────────────────────────────────────────────────


app = FastAPI(title="JWT Authentication API")


# ── API Endpoints ────────────────────────────────────────────────────────────


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Authenticate user and return tokens."""
    if req.username not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = users_db[req.username]
    if hash_password(req.password) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(req.username, user["role"])
    refresh_token = create_refresh_token(req.username)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE,
    )


@app.get("/protected")
async def protected_route(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Protected endpoint that requires valid JWT."""
    user_info = users_db.get(user["sub"], {})
    return {
        "message": f"Hello {user['sub']}!",
        "user_id": user["sub"],
        "role": user.get("role", "unknown"),
        "email": user_info.get("email", ""),
        "timestamp": time.time(),
    }


@app.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest) -> TokenResponse:
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_jwt(req.refresh_token, SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Check if refresh token is still valid in our store
    if req.refresh_token not in refresh_tokens:
        raise HTTPException(status_code=401, detail="Refresh token not found or expired")
    
    # Get user info
    if user_id not in users_db:
        raise HTTPException(status_code=401, detail="User not found")
    
    user = users_db[user_id]
    
    # Create new tokens
    new_access_token = create_access_token(user_id, user["role"])
    new_refresh_token = create_refresh_token(user_id)
    
    # Remove old refresh token
    if req.refresh_token in refresh_tokens:
        del refresh_tokens[req.refresh_token]
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE,
    )


@app.get("/users/me", response_model=UserInfo)
async def get_current_user_info(user: dict[str, Any] = Depends(get_current_user)) -> UserInfo:
    """Get current user information."""
    user_id = user["sub"]
    user_data = users_db.get(user_id, {})
    
    return UserInfo(
        user_id=user_id,
        role=user.get("role", "unknown"),
        email=user_data.get("email", ""),
    )


@app.post("/logout")
async def logout(refresh_token: str) -> dict[str, str]:
    """Logout by invalidating refresh token."""
    if refresh_token in refresh_tokens:
        del refresh_tokens[refresh_token]
    
    return {"message": "Logged out successfully"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": str(time.time())}
```

**注意**: 代码已按照约束要求修复，使用hmac和base64标准库实现JWT，无外部JWT库，所有功能在一个文件中实现。