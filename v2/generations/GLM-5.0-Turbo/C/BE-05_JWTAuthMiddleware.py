import hmac
import hashlib
import base64
import json
import time
import secrets
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="JWT Auth Middleware (Manual HMAC-SHA256)")

SECRET_KEY = "super-secret-key-change-in-production-2026"
TOKEN_EXPIRY = 1800  # 30 minutes
REFRESH_EXPIRY = 604800  # 7 days

security = HTTPBearer(auto_error=False)


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict, expiry_seconds: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload["iat"] = now
    payload["exp"] = now + expiry_seconds
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    return f"{signing_input}.{sig_b64}"


def verify_jwt(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid signature")
        payload = json.loads(base64url_decode(payload_b64))
        if "exp" in payload and payload["exp"] < int(time.time()):
            raise ValueError("Token expired")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    return verify_jwt(credentials.credentials)


# ---- Models ----

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---- Mock user store ----

USERS_DB = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

refresh_tokens: dict[str, dict] = {}


# ---- Endpoints ----

@app.post("/login")
def login(body: LoginRequest):
    username = body.username
    if username not in USERS_DB or USERS_DB[username]["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_payload = {"sub": username, "role": USERS_DB[username]["role"], "type": "access"}
    access_token = create_jwt(access_payload, TOKEN_EXPIRY)
    refresh_payload = {"sub": username, "role": USERS_DB[username]["role"], "type": "refresh", "jti": secrets.token_hex(16)}
    refresh_token = create_jwt(refresh_payload, REFRESH_EXPIRY)
    refresh_tokens[refresh_token] = {"sub": username, "used": False}
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRY,
    }


@app.get("/protected")
def protected(user: dict = Depends(get_current_user)):
    return {
        "message": "Access granted",
        "user": user["sub"],
        "role": user["role"],
    }


@app.post("/refresh")
def refresh(body: RefreshRequest):
    rt = body.refresh_token
    if rt not in refresh_tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if refresh_tokens[rt]["used"]:
        del refresh_tokens[rt]
        raise HTTPException(status_code=401, detail="Refresh token already used")
    payload = verify_jwt(rt)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    refresh_tokens[rt]["used"] = True
    username = payload["sub"]
    role = payload["role"]
    new_access = create_jwt({"sub": username, "role": role, "type": "access"}, TOKEN_EXPIRY)
    new_refresh_payload = {"sub": username, "role": role, "type": "refresh", "jti": secrets.token_hex(16)}
    new_rt = create_jwt(new_refresh_payload, REFRESH_EXPIRY)
    refresh_tokens[new_rt] = {"sub": username, "used": False}
    return {
        "access_token": new_access,
        "refresh_token": new_rt,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRY,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
