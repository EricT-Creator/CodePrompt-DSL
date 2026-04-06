from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict
import hmac
import hashlib
import base64
import json
import time
import uuid
from datetime import datetime, timedelta

app = FastAPI(title="JWT Authentication System")

# ===================== Data Models =====================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserData(BaseModel):
    username: str
    user_id: str
    scopes: list[str] = []

class RefreshRequest(BaseModel):
    refresh_token: str

# ===================== JWT Implementation =====================

class JWTManager:
    def __init__(self, secret_key: str = "your-secret-key-change-in-production"):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        
    def base64url_encode(self, data: bytes) -> str:
        encoded = base64.urlsafe_b64encode(data).decode('utf-8')
        return encoded.rstrip('=')
    
    def base64url_decode(self, data: str) -> bytes:
        padding = 4 - (len(data) % 4)
        data = data + ("=" * padding)
        return base64.urlsafe_b64decode(data)
    
    def create_token(self, payload: dict, token_type: str = "access") -> str:
        # Create header
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }
        header_b64 = self.base64url_encode(json.dumps(header).encode('utf-8'))
        
        # Add standard claims
        now = int(time.time())
        payload["iat"] = now
        payload["type"] = token_type
        
        if token_type == "access":
            payload["exp"] = now + 15 * 60  # 15 minutes
        elif token_type == "refresh":
            payload["exp"] = now + 7 * 24 * 60 * 60  # 7 days
        
        payload_b64 = self.base64url_encode(json.dumps(payload).encode('utf-8'))
        
        # Create signature
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            signing_input,
            hashlib.sha256
        ).digest()
        signature_b64 = self.base64url_encode(signature)
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def verify_token(self, token: str, expected_type: str = "access") -> Optional[dict]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Recreate signature
            signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signing_input,
                hashlib.sha256
            ).digest()
            expected_signature_b64 = self.base64url_encode(expected_signature)
            
            # Constant-time comparison
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None
            
            # Decode payload
            payload_json = self.base64url_decode(payload_b64)
            payload = json.loads(payload_json)
            
            # Check expiration
            if "exp" in payload and payload["exp"] < int(time.time()):
                return None
            
            # Check token type
            if payload.get("type") != expected_type:
                return None
            
            return payload
            
        except Exception:
            return None

# ===================== User Store =====================

class UserStore:
    def __init__(self):
        # Simulated user database
        self.users: Dict[str, dict] = {
            "user1": {
                "username": "user1",
                "password_hash": self._hash_password("password123"),
                "user_id": "u-001",
                "scopes": ["read", "write"]
            },
            "user2": {
                "username": "user2",
                "password_hash": self._hash_password("password456"),
                "user_id": "u-002",
                "scopes": ["read"]
            }
        }
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        user = self.users.get(username)
        if not user:
            return None
        
        hashed_input = self._hash_password(password)
        if hmac.compare_digest(hashed_input, user["password_hash"]):
            return {
                "username": user["username"],
                "user_id": user["user_id"],
                "scopes": user["scopes"]
            }
        return None

# ===================== Dependencies =====================

jwt_manager = JWTManager()
user_store = UserStore()
revoked_tokens = set()

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> UserData:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or malformed"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    payload = jwt_manager.verify_token(token, "access")
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return UserData(
        username=payload.get("username", ""),
        user_id=payload.get("sub", ""),
        scopes=payload.get("scopes", [])
    )

# ===================== API Endpoints =====================

@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = user_store.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create access token
    access_payload = {
        "sub": user["user_id"],
        "username": user["username"],
        "scopes": user["scopes"],
        "jti": str(uuid.uuid4())  # JWT ID for revocation tracking
    }
    access_token = jwt_manager.create_token(access_payload, "access")
    
    # Create refresh token
    refresh_payload = {
        "sub": user["user_id"],
        "username": user["username"],
        "jti": str(uuid.uuid4())
    }
    refresh_token = jwt_manager.create_token(refresh_payload, "refresh")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60  # 15 minutes in seconds
    )

@app.get("/protected")
async def protected_endpoint(current_user: UserData = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user.username}!",
        "user_id": current_user.user_id,
        "scopes": current_user.scopes,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    payload = jwt_manager.verify_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Check if token has been revoked
    if payload.get("jti") in revoked_tokens:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    
    user_id = payload.get("sub")
    username = payload.get("username")
    
    # Look up user to get scopes
    user_scopes = []
    for user in user_store.users.values():
        if user["user_id"] == user_id:
            user_scopes = user["scopes"]
            break
    
    # Revoke old refresh token
    revoked_tokens.add(payload.get("jti"))
    
    # Create new access token
    access_payload = {
        "sub": user_id,
        "username": username,
        "scopes": user_scopes,
        "jti": str(uuid.uuid4())
    }
    access_token = jwt_manager.create_token(access_payload, "access")
    
    # Create new refresh token
    refresh_payload = {
        "sub": user_id,
        "username": username,
        "jti": str(uuid.uuid4())
    }
    refresh_token = jwt_manager.create_token(refresh_payload, "refresh")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60  # 15 minutes in seconds
    )

@app.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    refresh_token: Optional[str] = None
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = jwt_manager.verify_token(token)
        if payload and payload.get("jti"):
            revoked_tokens.add(payload.get("jti"))
    
    if refresh_token:
        payload = jwt_manager.verify_token(refresh_token, "refresh")
        if payload and payload.get("jti"):
            revoked_tokens.add(payload.get("jti"))
    
    return {"message": "Successfully logged out"}

@app.get("/users/me")
async def get_current_user_info(current_user: UserData = Depends(get_current_user)):
    return current_user

# ===================== Admin Endpoints (for demonstration) =====================

@app.get("/admin/users")
async def list_users():
    users = []
    for username, user_data in user_store.users.items():
        users.append({
            "username": username,
            "user_id": user_data["user_id"],
            "scopes": user_data["scopes"]
        })
    return users

@app.get("/admin/revoked-tokens")
async def list_revoked_tokens():
    return list(revoked_tokens)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)