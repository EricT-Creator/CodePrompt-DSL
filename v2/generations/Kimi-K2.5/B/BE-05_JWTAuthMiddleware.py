import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse

app = FastAPI()

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY = 1800  # 30 minutes in seconds

# In-memory user store (replace with database in production)
USERS = {
    "admin": "password123",
    "user": "userpass"
}


def base64url_encode(data: bytes) -> str:
    """Base64URL encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def base64url_decode(data: str) -> bytes:
    """Base64URL decode, add padding if needed."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload: Dict[str, Any]) -> str:
    """Create a JWT token using HMAC-SHA256."""
    # Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    
    # Payload
    payload_encoded = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    
    # Signature
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    
    return f"{message}.{signature_encoded}"


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return payload if valid."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # Verify signature
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_encoded = base64url_encode(expected_signature)
        
        if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
            return None
        
        # Decode payload
        payload = json.loads(base64url_decode(payload_encoded))
        
        # Check expiration
        if payload.get('exp') and payload['exp'] < time.time():
            return None
        
        return payload
    except Exception:
        return None


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Dependency to get current user from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization[7:]  # Remove "Bearer "
    payload = verify_jwt(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload


@app.post("/login")
async def login(credentials: Dict[str, str]):
    """Authenticate user and return JWT token."""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    if username not in USERS or USERS[username] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    token = create_jwt(payload)
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY}


@app.get("/protected")
async def protected(user: Dict[str, Any] = Depends(get_current_user)):
    """Protected endpoint requiring valid JWT."""
    return {
        "message": "Access granted",
        "user": user.get("sub"),
        "issued_at": user.get("iat"),
        "expires_at": user.get("exp")
    }


@app.post("/refresh")
async def refresh(user: Dict[str, Any] = Depends(get_current_user)):
    """Refresh JWT token with new expiration time."""
    username = user.get("sub")
    
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY
    }
    
    new_token = create_jwt(payload)
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY
    }


@app.get("/public")
async def public():
    """Public endpoint that doesn't require authentication."""
    return {"message": "This is a public endpoint"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
