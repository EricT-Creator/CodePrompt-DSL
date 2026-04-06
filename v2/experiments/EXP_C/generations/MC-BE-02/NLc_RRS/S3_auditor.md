# MC-BE-02 代码审查报告

## Constraint Review
- C1 (Python + FastAPI): PASS — 使用Python和FastAPI框架创建API应用
- C2 (Manual JWT, no PyJWT): PASS — 使用hmac+base64手动实现JWT（create_jwt、verify_jwt函数），没有使用PyJWT库
- C3 (stdlib + fastapi only): FAIL — 使用了pydantic库（用于数据验证），不符合"stdlib + fastapi + uvicorn only"的严格约束
- C4 (Single file): PASS — 所有代码在单个文件中
- C5 (login/protected/refresh endpoints): PASS — 实现了/login、/protected、/refresh三个端点
- C6 (Code only): PASS — 只有Python代码，没有外部配置文件或资源

## Functionality Assessment (0-5)
Score: 4.5 — 代码实现了完整的JWT认证系统，功能包括：手动JWT生成与验证（HS256算法）、访问令牌/刷新令牌双机制、令牌过期时间、用户验证、受保护端点、令牌刷新。代码结构清晰，安全实现正确。扣分点：使用了pydantic，不符合"stdlib only"的严格约束。

## Corrected Code
由于C3约束失败（要求stdlib + fastapi only，但使用了pydantic），需要移除pydantic依赖。以下是修正后的代码：

```py
import hmac
import hashlib
import base64
import json
import time
from typing import Any
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Depends, Header


# ── Configuration ──

SECRET_KEY = "super-secret-key-for-jwt-signing-2026"
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days

# ── User Store ──

users: dict[str, str] = {
    "admin": "password123",
    "user1": "pass456",
}

# ── Refresh Token Tracking ──

valid_refresh_tokens: set[str] = set()


# ── Request / Response Models (using dataclasses instead of pydantic) ──

@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class LoginResponse:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass
class RefreshRequest:
    refresh_token: str


@dataclass
class RefreshResponse:
    access_token: str
    token_type: str = "bearer"


@dataclass
class ProtectedResponse:
    user: str
    message: str


# ── Base64URL Helpers ──

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ── JWT Functions ──

def create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    encoded_header, encoded_payload, encoded_signature = parts

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = base64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid signature")

    payload_bytes = base64url_decode(encoded_payload)
    payload = json.loads(payload_bytes)

    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token expired")

    return payload


def create_access_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_EXPIRE),
        "type": "access",
    }
    return create_jwt(payload)


def create_refresh_token(username: str) -> str:
    now = time.time()
    payload = {
        "sub": username,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_EXPIRE),
        "type": "refresh",
    }
    token = create_jwt(payload)
    valid_refresh_tokens.add(token)
    return token


# ── FastAPI Dependency ──

async def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]

    try:
        payload = verify_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return username


# ── App ──

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    stored_password = users.get(body.username)
    if stored_password is None or stored_password != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(body.username)
    refresh_token = create_refresh_token(body.username)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected(user: str = Depends(get_current_user)) -> ProtectedResponse:
    return ProtectedResponse(user=user, message="Access granted")


@app.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest) -> RefreshResponse:
    try:
        payload = verify_jwt(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if body.refresh_token in valid_refresh_tokens:
        valid_refresh_tokens.discard(body.refresh_token)

    access_token = create_access_token(username)

    return RefreshResponse(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```