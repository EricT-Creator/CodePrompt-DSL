import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, Optional, Set

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = "your-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRY = 900
REFRESH_TOKEN_EXPIRY = 604800

revoked_tokens: Set[str] = set()

users: Dict[str, Dict[str, str]] = {
    "user1": {
        "username": "user1",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "user_id": "u-001"
    },
    "user2": {
        "username": "user2",
        "password_hash": hashlib.sha256("password456".encode()).hexdigest(),
        "user_id": "u-002"
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    user_id: str
    username: str

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def create_jwt(payload: Dict[str, any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    return f"{signing_input}.{signature_b64}"

def verify_jwt(token: str, secret: str) -> Optional[Dict[str, any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        expected_signature_b64 = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def create_tokens(user_id: str, username: str) -> tuple[str, str]:
    now = int(time.time())
    access_payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRY,
        "type": "access",
        "jti": str(uuid.uuid4())
    }
    refresh_payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRY,
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }
    return create_jwt(access_payload, SECRET_KEY), create_jwt(refresh_payload, SECRET_KEY)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    token = credentials.credentials
    payload = verify_jwt(token, SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return UserResponse(user_id=payload["sub"], username=payload["username"])

@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = users.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token, refresh_token = create_tokens(user["user_id"], user["username"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@app.get("/protected")
async def protected(user: UserResponse = Depends(get_current_user)):
    return {"message": f"Hello {user.username}", "user_id": user.user_id}

@app.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    payload = verify_jwt(request.refresh_token, SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    jti = payload.get("jti")
    if jti in revoked_tokens:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    if jti:
        revoked_tokens.add(jti)
    access_token, refresh_token = create_tokens(payload["sub"], payload["username"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
