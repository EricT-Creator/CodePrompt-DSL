import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# JWT implementation without external libraries
class JWTEncoder:
    def __init__(self, secret_key: str = "supersecretkey"):
        self.secret_key = secret_key.encode()
    
    def base64_url_encode(self, data: bytes) -> str:
        """Base64 URL encode without padding"""
        encoded = base64.urlsafe_b64encode(data).rstrip(b'=')
        return encoded.decode('utf-8')
    
    def base64_url_decode(self, data: str) -> bytes:
        """Base64 URL decode with padding restoration"""
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    def sign(self, header: str, payload: str) -> str:
        """Create HMAC SHA256 signature"""
        message = f"{header}.{payload}".encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
        return self.base64_url_encode(signature)
    
    def encode(self, payload: Dict) -> str:
        """Encode JWT token"""
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self.base64_url_encode(json.dumps(header).encode())
        
        # Add expiry time (30 minutes)
        payload_with_exp = payload.copy()
        payload_with_exp['exp'] = int(time.time()) + 1800  # 30 minutes
        payload_b64 = self.base64_url_encode(json.dumps(payload_with_exp).encode())
        
        signature = self.sign(header_b64, payload_b64)
        return f"{header_b64}.{payload_b64}.{signature}"
    
    def decode(self, token: str) -> Tuple[Optional[Dict], Optional[Dict], bool]:
        """Decode and verify JWT token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None, None, False
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Verify signature
            expected_signature = self.sign(header_b64, payload_b64)
            if not hmac.compare_digest(signature_b64, expected_signature):
                return None, None, False
            
            # Decode header and payload
            header_json = self.base64_url_decode(header_b64)
            payload_json = self.base64_url_decode(payload_b64)
            
            header = json.loads(header_json)
            payload = json.loads(payload_json)
            
            # Check expiry
            if 'exp' in payload and payload['exp'] < time.time():
                return header, payload, False
            
            return header, payload, True
            
        except Exception:
            return None, None, False

# FastAPI app and models
app = FastAPI(title="JWT Auth API")
security = HTTPBearer()
jwt_encoder = JWTEncoder()

# In-memory user store (for demo)
users_db = {
    "alice": {"password": "password123", "role": "user"},
    "bob": {"password": "securepass", "role": "admin"},
}

# Refresh token store
refresh_tokens = {}

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800

class RefreshRequest(BaseModel):
    refresh_token: str

class ProtectedResponse(BaseModel):
    message: str
    user: str
    role: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Middleware to verify JWT token"""
    token = credentials.credentials
    header, payload, valid = jwt_encoder.decode(token)
    
    if not valid or not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

# Routes
@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    user = users_db.get(request.username)
    
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    payload = {
        "sub": request.username,
        "role": user["role"],
        "iat": int(time.time()),
    }
    
    access_token = jwt_encoder.encode(payload)
    
    # Create refresh token (simplified version)
    refresh_token = base64.urlsafe_b64encode(
        f"{request.username}:{int(time.time())}".encode()
    ).decode()
    
    refresh_tokens[refresh_token] = {
        "username": request.username,
        "created_at": int(time.time()),
    }
    
    return TokenResponse(access_token=access_token)

@app.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token"""
    if request.refresh_token not in refresh_tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    token_data = refresh_tokens[request.refresh_token]
    
    # Check if refresh token is expired (e.g., 7 days)
    if time.time() - token_data["created_at"] > 604800:
        del refresh_tokens[request.refresh_token]
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    username = token_data["username"]
    user = users_db.get(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Create new access token
    payload = {
        "sub": username,
        "role": user["role"],
        "iat": int(time.time()),
    }
    
    access_token = jwt_encoder.encode(payload)
    
    # Create new refresh token (rotate)
    new_refresh_token = base64.urlsafe_b64encode(
        f"{username}:{int(time.time())}".encode()
    ).decode()
    
    refresh_tokens[new_refresh_token] = {
        "username": username,
        "created_at": int(time.time()),
    }
    
    # Remove old refresh token
    del refresh_tokens[request.refresh_token]
    
    return TokenResponse(access_token=access_token)

@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(payload: Dict = Depends(verify_token)):
    """Protected endpoint requiring valid JWT"""
    username = payload.get("sub", "unknown")
    role = payload.get("role", "user")
    
    return ProtectedResponse(
        message=f"Hello {username}, you have access to protected content!",
        user=username,
        role=role,
    )

@app.get("/status")
async def status():
    """Service status endpoint"""
    return {
        "status": "running",
        "users_count": len(users_db),
        "active_refresh_tokens": len(refresh_tokens),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)