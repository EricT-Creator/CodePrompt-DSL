from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Dict, Optional, Literal
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

SECRET_KEY = "your-secret-key-change-in-production"

TokenType = Literal["access", "refresh"]


@dataclass
class JWTPayload:
    sub: str
    username: str
    iat: int
    exp: int
    type: TokenType


class JWTUtil:
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

    @staticmethod
    def _base64url_decode(s: str) -> bytes:
        padding = 4 - len(s) % 4
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s)

    @staticmethod
    def _create_signature(header_b64: str, payload_b64: str) -> str:
        signing_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        return JWTUtil._base64url_encode(signature)

    @staticmethod
    def create_token(username: str, user_id: str, token_type: TokenType) -> str:
        now = int(time.time())
        if token_type == "access":
            exp = now + 3600  # 1 hour
        else:
            exp = now + 604800  # 7 days

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "username": username,
            "iat": now,
            "exp": exp,
            "type": token_type
        }

        header_b64 = JWTUtil._base64url_encode(json.dumps(header, separators=(',', ':')).encode())
        payload_b64 = JWTUtil._base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
        signature = JWTUtil._create_signature(header_b64, payload_b64)

        return f"{header_b64}.{payload_b64}.{signature}"

    @staticmethod
    def verify_token(token: str, expected_type: TokenType) -> JWTPayload:
        parts = token.split('.')
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token format")

        header_b64, payload_b64, signature_b64 = parts

        expected_signature = JWTUtil._create_signature(header_b64, payload_b64)
        if not hmac.compare_digest(signature_b64, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid token signature")

        try:
            payload_bytes = JWTUtil._base64url_decode(payload_b64)
            payload = json.loads(payload_bytes)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token expired")

        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail=f"Expected {expected_type} token")

        return JWTPayload(
            sub=payload["sub"],
            username=payload["username"],
            iat=payload["iat"],
            exp=payload["exp"],
            type=payload["type"]
        )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


USERS: Dict[str, Dict[str, str]] = {
    "john": {"password_hash": hash_password("password123"), "user_id": "u001"},
    "jane": {"password_hash": hash_password("password456"), "user_id": "u002"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ProtectedResponse(BaseModel):
    message: str
    user: str


def extract_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    return parts[1]


async def require_auth(request: Request) -> JWTPayload:
    token = extract_token(request)
    return JWTUtil.verify_token(token, "access")


async def require_refresh_token(request: Request) -> JWTPayload:
    token = extract_token(request)
    return JWTUtil.verify_token(token, "refresh")


app = FastAPI(title="JWT Auth Middleware API")


@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = USERS.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_hash = hash_password(request.password)
    if password_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = JWTUtil.create_token(request.username, user["user_id"], "access")
    refresh_token = JWTUtil.create_token(request.username, user["user_id"], "refresh")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected(payload: JWTPayload = Depends(require_auth)) -> ProtectedResponse:
    return ProtectedResponse(
        message="You have accessed a protected endpoint",
        user=payload.username
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh(payload: JWTPayload = Depends(require_refresh_token)) -> TokenResponse:
    new_access_token = JWTUtil.create_token(payload.username, payload.sub, "access")
    new_refresh_token = JWTUtil.create_token(payload.username, payload.sub, "refresh")

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )
