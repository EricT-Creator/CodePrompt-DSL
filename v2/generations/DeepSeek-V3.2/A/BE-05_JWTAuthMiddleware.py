import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    token: str

class ProtectedResponse(BaseModel):
    message: str
    user: str
    issued_at: int
    expires_at: int

# JWT implementation using standard library only
class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key.encode('utf-8')
        self.algorithm = algorithm
        
    def _base64url_encode(self, data: bytes) -> str:
        """Base64URL encode without padding."""
        encoded = base64.urlsafe_b64encode(data).rstrip(b'=')
        return encoded.decode('utf-8')
    
    def _base64url_decode(self, data: str) -> bytes:
        """Base64URL decode with padding."""
        padding = 4 - (len(data) % 4)
        data = data + ("=" * padding)
        return base64.urlsafe_b64decode(data)
    
    def _sign(self, message: bytes) -> bytes:
        """Create HMAC SHA256 signature."""
        return hmac.new(self.secret_key, message, hashlib.sha256).digest()
    
    def encode(self, payload: Dict) -> str:
        """Encode a JWT token."""
        # Create header
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }
        
        # Encode header and payload
        header_encoded = self._base64url_encode(json.dumps(header).encode('utf-8'))
        payload_encoded = self._base64url_encode(json.dumps(payload).encode('utf-8'))
        
        # Create signature
        message = f"{header_encoded}.{payload_encoded}".encode('utf-8')
        signature = self._sign(message)
        signature_encoded = self._base64url_encode(signature)
        
        return f"{header_encoded}.{payload_encoded}.{signature_encoded}"
    
    def decode(self, token: str) -> Optional[Dict]:
        """Decode and verify a JWT token."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
                
            header_encoded, payload_encoded, signature_encoded = parts
            
            # Verify signature
            message = f"{header_encoded}.{payload_encoded}".encode('utf-8')
            expected_signature = self._sign(message)
            provided_signature = self._base64url_decode(signature_encoded)
            
            if not hmac.compare_digest(expected_signature, provided_signature):
                return None
            
            # Decode payload
            payload_json = self._base64url_decode(payload_encoded)
            payload = json.loads(payload_json)
            
            return payload
            
        except Exception:
            return None

# FastAPI app
app = FastAPI(title="JWT Authentication API", version="1.0.0")

# JWT manager instance
jwt_manager = JWTManager(secret_key="your-secret-key-change-in-production")

# In-memory user store (for demonstration)
users = {
    "alice": {"password": "password123", "role": "user"},
    "bob": {"password": "bobpass", "role": "admin"},
    "charlie": {"password": "charliepass", "role": "user"},
}

# Token blacklist for logout (simple in-memory for demo)
token_blacklist = set()

# Security scheme
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Tuple[str, Dict]:
    """Dependency to get current user from JWT token."""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if token in token_blacklist:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    # Decode token
    payload = jwt_manager.decode(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check expiration
    current_time = int(time.time())
    if payload.get("exp", 0) < current_time:
        raise HTTPException(status_code=401, detail="Token has expired")
    
    return payload.get("sub"), payload

def create_access_token(username: str, expires_in_minutes: int = 30) -> str:
    """Create a new access token."""
    current_time = int(time.time())
    payload = {
        "sub": username,
        "iat": current_time,
        "exp": current_time + (expires_in_minutes * 60),
        "role": users.get(username, {}).get("role", "user"),
        "jti": hashlib.sha256(f"{username}{current_time}".encode()).hexdigest()[:16]
    }
    return jwt_manager.encode(payload)

@app.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Login endpoint to obtain JWT token."""
    user = users.get(login_data.username)
    if not user or user["password"] != login_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(login_data.username)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=30 * 60  # 30 minutes in seconds
    )

@app.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_data: RefreshRequest):
    """Refresh an access token."""
    token = refresh_data.token
    
    # Verify the token
    payload = jwt_manager.decode(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check expiration
    current_time = int(time.time())
    if payload.get("exp", 0) < current_time:
        raise HTTPException(status_code=401, detail="Token has expired")
    
    # Get username from token
    username = payload.get("sub")
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Create new token
    new_token = create_access_token(username)
    
    # Optionally blacklist the old token
    token_blacklist.add(token)
    
    return TokenResponse(
        access_token=new_token,
        expires_in=30 * 60
    )

@app.get("/protected", response_model=ProtectedResponse)
async def protected_endpoint(user_info: Tuple[str, Dict] = Depends(get_current_user)):
    """Protected endpoint that requires valid JWT."""
    username, payload = user_info
    
    return ProtectedResponse(
        message="Access granted to protected resource",
        user=username,
        issued_at=payload.get("iat", 0),
        expires_at=payload.get("exp", 0)
    )

@app.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout endpoint to blacklist token."""
    token = credentials.credentials
    token_blacklist.add(token)
    return {"message": "Successfully logged out"}

@app.get("/status")
async def get_token_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get status of current token."""
    username, payload = get_current_user(credentials)
    
    current_time = int(time.time())
    expires_at = payload.get("exp", 0)
    time_remaining = max(0, expires_at - current_time)
    
    return {
        "user": username,
        "role": payload.get("role"),
        "issued_at": datetime.fromtimestamp(payload.get("iat", 0)).isoformat(),
        "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
        "time_remaining_seconds": time_remaining,
        "time_remaining_minutes": time_remaining // 60,
        "token_id": payload.get("jti"),
        "is_blacklisted": credentials.credentials in token_blacklist
    }

@app.exception_handler(HTTPException)
async def jwt_exception_handler(request, exc):
    """Custom exception handler for JWT errors."""
    if exc.status_code == 401:
        return {
            "error": "Unauthorized",
            "message": exc.detail,
            "status_code": 401
        }
    return exc

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "JWT Authentication API",
        "endpoints": {
            "POST /login": "Login with username/password",
            "POST /refresh": "Refresh access token",
            "GET /protected": "Protected endpoint (requires JWT)",
            "POST /logout": "Logout (blacklist token)",
            "GET /status": "Check token status"
        },
        "users": list(users.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)