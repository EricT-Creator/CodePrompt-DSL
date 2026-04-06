import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# ==================== Configuration ====================

SECRET_KEY = "your-256-bit-secret-key-change-this-in-production"
ACCESS_TOKEN_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7
ALGORITHM = "HS256"
TOKEN_TYPE = "JWT"


# ==================== Data Models ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ProtectedResponse(BaseModel):
    user: str
    message: str


# ==================== Internal Data Classes ====================

@dataclass
class TokenPayload:
    sub: str  # username
    iat: float  # issued at timestamp
    exp: float  # expiration timestamp
    typ: str  # token type: "access" or "refresh"


# ==================== User Store (Simple In-Memory) ====================

class UserStore:
    def __init__(self):
        self._users: Dict[str, str] = {
            "admin": "password123",
            "user1": "pass456"
        }
    
    def authenticate(self, username: str, password: str) -> bool:
        stored_password = self._users.get(username)
        return stored_password == password
    
    def get_user(self, username: str) -> Optional[str]:
        return self._users.get(username)
    
    def add_user(self, username: str, password: str):
        self._users[username] = password


# ==================== JWT Utilities ====================

class JWTError(Exception):
    pass


def base64url_encode(data: bytes) -> str:
    encoded = base64.urlsafe_b64encode(data).decode('utf-8')
    return encoded.rstrip('=')


def base64url_decode(encoded: str) -> bytes:
    # Add padding if needed
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded)


def create_jwt(payload: Dict[str, any]) -> str:
    # Header is static for this implementation
    header = {"alg": ALGORITHM, "typ": TOKEN_TYPE}
    
    # Encode header and payload
    encoded_header = base64url_encode(json.dumps(header).encode('utf-8'))
    encoded_payload = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    # Create signature
    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        signing_input,
        hashlib.sha256
    ).digest()
    
    encoded_signature = base64url_encode(signature)
    
    # Combine all parts
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str) -> TokenPayload:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise JWTError("Invalid token format")
        
        encoded_header, encoded_payload, encoded_signature = parts
        
        # Verify signature
        signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        expected_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            signing_input,
            hashlib.sha256
        ).digest()
        
        received_signature = base64url_decode(encoded_signature)
        
        if not hmac.compare_digest(expected_signature, received_signature):
            raise JWTError("Invalid signature")
        
        # Decode payload
        payload_json = base64url_decode(encoded_payload).decode('utf-8')
        payload_dict = json.loads(payload_json)
        
        # Check expiration
        current_time = time.time()
        if payload_dict['exp'] < current_time:
            raise JWTError("Token expired")
        
        return TokenPayload(
            sub=payload_dict['sub'],
            iat=payload_dict['iat'],
            exp=payload_dict['exp'],
            typ=payload_dict.get('typ', 'access')
        )
    
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise JWTError(f"Token decoding error: {str(e)}")


def create_access_token(username: str) -> str:
    now = time.time()
    expires = now + (ACCESS_TOKEN_EXPIRY_MINUTES * 60)
    
    payload = {
        "sub": username,
        "iat": now,
        "exp": expires,
        "typ": "access"
    }
    
    return create_jwt(payload)


def create_refresh_token(username: str) -> str:
    now = time.time()
    expires = now + (REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60)
    
    payload = {
        "sub": username,
        "iat": now,
        "exp": expires,
        "typ": "refresh"
    }
    
    return create_jwt(payload)


def verify_access_token(token: str) -> TokenPayload:
    payload = verify_jwt(token)
    if payload.typ != "access":
        raise JWTError("Invalid token type, expected access token")
    return payload


def verify_refresh_token(token: str) -> TokenPayload:
    payload = verify_jwt(token)
    if payload.typ != "refresh":
        raise JWTError("Invalid token type, expected refresh token")
    return payload


# ==================== FastAPI Dependencies ====================

security = HTTPBearer()

user_store = UserStore()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_access_token(credentials.credentials)
        return payload.sub
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


# ==================== FastAPI Application ====================

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Authenticate user
    if not user_store.authenticate(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Create tokens
    access_token = create_access_token(request.username)
    refresh_token = create_refresh_token(request.username)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(user: str = Depends(get_current_user)):
    return ProtectedResponse(
        user=user,
        message="Access granted"
    )


@app.post("/refresh", response_model=LoginResponse)
async def refresh(request: RefreshRequest):
    try:
        payload = verify_refresh_token(request.refresh_token)
        
        # Create new tokens
        access_token = create_access_token(payload.sub)
        refresh_token = create_refresh_token(payload.sub)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "jwt-auth"
    }


# ==================== Demo Endpoints (for testing) ====================

class DemoUserRequest(BaseModel):
    username: str
    password: str


@app.post("/demo/add_user")
async def add_demo_user(request: DemoUserRequest):
    user_store.add_user(request.username, request.password)
    return {"message": f"User {request.username} added successfully"}


@app.get("/demo/users")
async def list_demo_users():
    users = list(user_store._users.keys())
    return {"users": users, "count": len(users)}


# ==================== Main Execution ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)