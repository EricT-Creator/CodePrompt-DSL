"""
JWT Authentication Middleware for FastAPI - Manual Implementation

This module implements a complete JWT authentication system from scratch,
without any external JWT libraries. It handles login, protected endpoints,
and token refresh with manual HMAC-SHA256 signing and verification.
"""

import base64
import hmac
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ============================================================================
# Configuration & Constants
# ============================================================================

SECRET_KEY = "supersecretkey_do_not_use_in_production_change_this"
ALGORITHM = "HS256"
TOKEN_TYPE = "JWT"

ACCESS_TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY_SECONDS = 604800  # 7 days

# Mock user database
USERS = {
    "john": {
        "user_id": "u001",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "username": "john"
    },
    "jane": {
        "user_id": "u002",
        "password_hash": hashlib.sha256("password456".encode()).hexdigest(),
        "username": "jane"
    }
}

# ============================================================================
# Base64URL Encoding/Decoding
# ============================================================================

def base64url_encode(data: bytes) -> str:
    """Encode bytes to Base64URL string without padding."""
    encoded = base64.urlsafe_b64encode(data).decode('utf-8')
    return encoded.rstrip('=')

def base64url_decode(encoded: str) -> bytes:
    """Decode Base64URL string to bytes, restoring padding."""
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded)

# ============================================================================
# JWT Encoding/Decoding
# ============================================================================

def create_jwt(payload: Dict[str, Any]) -> str:
    """
    Create a JWT token from the given payload.
    
    Steps:
    1. Create header with alg and typ
    2. Base64URL encode header
    3. Base64URL encode payload
    4. Compute HMAC-SHA256 signature
    5. Assemble token: header.payload.signature
    """
    # Create header
    header = {
        "alg": ALGORITHM,
        "typ": TOKEN_TYPE
    }
    
    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    
    # Create signing input
    signing_input = f"{header_b64}.{payload_b64}".encode()
    
    # Compute signature
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input,
        hashlib.sha256
    ).digest()
    
    # Encode signature
    signature_b64 = base64url_encode(signature)
    
    # Assemble token
    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
    return token

def verify_jwt(token: str, expected_type: Optional[Literal["access", "refresh"]] = None) -> Dict[str, Any]:
    """
    Verify a JWT token and return the decoded payload if valid.
    
    Raises HTTPException with 401 status code for invalid tokens.
    """
    # Split token into parts
    parts = token.split('.')
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    header_b64, payload_b64, signature_b64 = parts
    
    # Reconstruct signing input
    signing_input = f"{header_b64}.{payload_b64}".encode()
    
    # Recompute signature
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input,
        hashlib.sha256
    ).digest()
    expected_signature_b64 = base64url_encode(expected_signature)
    
    # Constant-time signature comparison
    if not hmac.compare_digest(signature_b64, expected_signature_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature"
        )
    
    # Decode payload
    try:
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check expiration
    current_time = time.time()
    if "exp" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing expiration"
        )
    
    if payload["exp"] < current_time:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    # Check token type if specified
    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token type mismatch, expected {expected_type}"
        )
    
    return payload

# ============================================================================
# Token Creation Utilities
# ============================================================================

def create_access_token(user_id: str, username: str) -> str:
    """Create a short-lived access token."""
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(time.time()),
        "exp": int(time.time() + ACCESS_TOKEN_EXPIRY_SECONDS),
        "type": "access",
        "jti": str(uuid.uuid4())  # Unique token ID
    }
    return create_jwt(payload)

def create_refresh_token(user_id: str, username: str) -> str:
    """Create a long-lived refresh token."""
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(time.time()),
        "exp": int(time.time() + REFRESH_TOKEN_EXPIRY_SECONDS),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }
    return create_jwt(payload)

# ============================================================================
# Token Extraction
# ============================================================================

def extract_token(request: Request) -> str:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format"
        )
    
    return parts[1]

# ============================================================================
# Dependencies (Authentication Middleware)
# ============================================================================

async def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency for endpoints requiring a valid access token."""
    token = extract_token(request)
    return verify_jwt(token, expected_type="access")

async def require_refresh_token(request: Request) -> Dict[str, Any]:
    """Dependency for refresh endpoint requiring a valid refresh token."""
    token = extract_token(request)
    return verify_jwt(token, expected_type="refresh")

# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="Access token for API calls")
    refresh_token: str = Field(..., description="Refresh token for obtaining new access tokens")
    token_type: str = Field("bearer", description="Type of token")
    expires_in: int = Field(ACCESS_TOKEN_EXPIRY_SECONDS, description="Access token lifetime in seconds")
    user_id: str = Field(..., description="User ID")

class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Refresh token (can also be in Authorization header)")

class RefreshResponse(BaseModel):
    access_token: str = Field(..., description="New access token")
    refresh_token: str = Field(..., description="New refresh token (refresh token rotation)")
    token_type: str = Field("bearer", description="Type of token")
    expires_in: int = Field(ACCESS_TOKEN_EXPIRY_SECONDS, description="Access token lifetime in seconds")

class ProtectedResponse(BaseModel):
    message: str = Field(..., description="Protected endpoint message")
    user_info: Dict[str, Any] = Field(..., description="User information from token")

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="JWT Authentication API",
    description="Manual JWT implementation with login, protected endpoints, and token refresh",
    version="1.0.0"
)

# ============================================================================
# API Endpoints
# ============================================================================

@app.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate user and obtain tokens",
    description="Authenticate with username and password, receive access and refresh tokens."
)
async def login(login_data: LoginRequest):
    """Authenticate user and issue JWT tokens."""
    # Check if user exists
    if login_data.username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    user = USERS[login_data.username]
    
    # Verify password
    password_hash = hashlib.sha256(login_data.password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    access_token = create_access_token(user["user_id"], user["username"])
    refresh_token = create_refresh_token(user["user_id"], user["username"])
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user["user_id"]
    )

@app.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to obtain new access and refresh tokens."
)
async def refresh(
    refresh_data: Optional[RefreshRequest] = None,
    token_payload: Dict[str, Any] = Depends(require_refresh_token)
):
    """Exchange a valid refresh token for new tokens."""
    # Extract token from request body if provided, otherwise use Authorization header
    if refresh_data and refresh_data.refresh_token:
        token = refresh_data.refresh_token
        # Verify the provided refresh token
        token_payload = verify_jwt(token, expected_type="refresh")
    # Otherwise, token_payload already contains verified payload from require_refresh_token
    
    user_id = token_payload["sub"]
    username = token_payload["username"]
    
    # Create new tokens
    access_token = create_access_token(user_id, username)
    refresh_token = create_refresh_token(user_id, username)
    
    return RefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@app.get(
    "/protected",
    response_model=ProtectedResponse,
    summary="Access protected resource",
    description="Example endpoint that requires a valid access token."
)
async def protected(user_info: Dict[str, Any] = Depends(require_auth)):
    """Protected endpoint that requires authentication."""
    return ProtectedResponse(
        message=f"Hello {user_info['username']}! You have accessed a protected resource.",
        user_info=user_info
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

# ============================================================================
# Error Handling
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"WWW-Authenticate": "Bearer"}
    )

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)