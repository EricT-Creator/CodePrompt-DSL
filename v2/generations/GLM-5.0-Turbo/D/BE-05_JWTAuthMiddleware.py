"""
JWT认证中间件 - 手动HMAC-SHA256实现
不使用PyJWT/jose等JWT库，仅用hmac+base64标准库
"""

import hmac
import hashlib
import base64
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

SECRET_KEY = "my-secret-key-2026"
ACCESS_TOKEN_EXPIRE = 30 * 60  # 30 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days

app = FastAPI(title="JWT Auth Middleware (Manual HMAC-SHA256)")

# ===== 手动JWT实现 =====

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def _json_dumps(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")

def create_jwt(payload: dict, secret: str, expires_in: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload["iat"] = now
    payload["exp"] = now + expires_in

    header_b64 = base64url_encode(_json_dumps(header))
    payload_b64 = base64url_encode(_json_dumps(payload))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_jwt(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(base64url_decode(payload_b64))

        if "exp" in payload and payload["exp"] < int(time.time()):
            return None

        return payload
    except Exception:
        return None

# ===== 数据模型 =====

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# ===== 内存存储 =====

refresh_tokens: dict[str, dict] = {}

# 用户模拟数据
USERS = {
    "admin": "password123",
    "user1": "pass456",
}

def authenticate_user(username: str, password: str) -> bool:
    return USERS.get(username) == password

# ===== 依赖注入 =====

async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证令牌")
    token = auth_header[7:]
    payload = verify_jwt(token, SECRET_KEY)
    if payload is None:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return payload

# ===== 路由 =====

@app.post("/login")
async def login(req: LoginRequest):
    if not authenticate_user(req.username, req.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_jwt(
        {"sub": req.username, "type": "access"},
        SECRET_KEY,
        ACCESS_TOKEN_EXPIRE,
    )
    refresh_token = create_jwt(
        {"sub": req.username, "type": "refresh"},
        SECRET_KEY,
        REFRESH_TOKEN_EXPIRE,
    )

    refresh_tokens[refresh_token] = {"username": req.username}

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE,
    }

@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)):
    return {
        "message": f"你好，{user['sub']}！你已通过认证。",
        "user": user["sub"],
        "type": user.get("type"),
        "iat": user.get("iat"),
        "exp": user.get("exp"),
    }

@app.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = verify_jwt(req.refresh_token, SECRET_KEY)
    if payload is None:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")

    if req.refresh_token not in refresh_tokens:
        raise HTTPException(status_code=401, detail="刷新令牌已被撤销")

    username = payload["sub"]
    new_access_token = create_jwt(
        {"sub": username, "type": "access"},
        SECRET_KEY,
        ACCESS_TOKEN_EXPIRE,
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE,
    }

# ===== 全局异常处理 =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
