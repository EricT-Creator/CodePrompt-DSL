import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# 手动实现JWT相关功能
class JWTUtils:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def base64url_encode(self, data: bytes) -> str:
        """Base64 URL安全编码"""
        encoded = base64.urlsafe_b64encode(data).rstrip(b'=')
        return encoded.decode('utf-8')
    
    def base64url_decode(self, data: str) -> bytes:
        """Base64 URL安全解码"""
        padding = 4 - (len(data) % 4)
        data = data + ('=' * padding)
        return base64.urlsafe_b64decode(data)
    
    def create_signature(self, header: str, payload: str) -> str:
        """创建HMAC-SHA256签名"""
        if self.algorithm != "HS256":
            raise ValueError(f"不支持的算法: {self.algorithm}")
        
        message = f"{header}.{payload}".encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).digest()
        
        return self.base64url_encode(signature)
    
    def create_token(self, payload: Dict) -> str:
        """创建JWT令牌"""
        # 创建header
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }
        header_encoded = self.base64url_encode(json.dumps(header).encode('utf-8'))
        
        # 添加过期时间
        payload_with_exp = payload.copy()
        payload_with_exp["exp"] = int(time.time()) + 1800  # 30分钟过期
        
        payload_encoded = self.base64url_encode(json.dumps(payload_with_exp).encode('utf-8'))
        
        # 创建签名
        signature = self.create_signature(header_encoded, payload_encoded)
        
        return f"{header_encoded}.{payload_encoded}.{signature}"
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """验证JWT令牌"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature = parts
            
            # 验证签名
            expected_signature = self.create_signature(header_encoded, payload_encoded)
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # 解码payload
            payload_json = self.base64url_decode(payload_encoded)
            payload = json.loads(payload_json)
            
            # 检查过期时间
            if "exp" in payload:
                if payload["exp"] < time.time():
                    return None
            
            return payload
            
        except Exception:
            return None

# 数据模型
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
    user_info: Dict
    token_expires_at: int

class StatusResponse(BaseModel):
    message: str
    current_time: str
    token_count: int

# 简单的用户存储（生产环境应使用数据库）
users_db = {
    "alice": {
        "password": "password123",
        "role": "user",
        "full_name": "Alice Smith"
    },
    "bob": {
        "password": "secret456",
        "role": "admin",
        "full_name": "Bob Johnson"
    }
}

# 存储刷新令牌（生产环境应使用Redis等）
refresh_tokens_db: Dict[str, Dict] = {}

# JWT配置
SECRET_KEY = "your-secret-key-change-in-production"  # 生产环境应使用环境变量
jwt_utils = JWTUtils(SECRET_KEY)

# FastAPI应用
app = FastAPI(title="JWT认证服务", description="手动实现JWT认证的FastAPI服务")

# 安全依赖
security = HTTPBearer()

def verify_token_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """验证令牌的依赖项"""
    token = credentials.credentials
    payload = jwt_utils.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return payload

# API端点
@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """登录并获取令牌"""
    user = users_db.get(request.username)
    
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 创建访问令牌
    access_token_payload = {
        "sub": request.username,
        "role": user["role"],
        "name": user["full_name"],
        "iat": int(time.time())
    }
    access_token = jwt_utils.create_token(access_token_payload)
    
    # 创建刷新令牌（简单实现，生产环境应更安全）
    refresh_token = f"refresh_{int(time.time())}_{request.username}"
    refresh_tokens_db[refresh_token] = {
        "username": request.username,
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + 7 * 24 * 3600  # 7天过期
    }
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800
    )

@app.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """刷新访问令牌"""
    refresh_token = request.refresh_token
    
    if not refresh_token.startswith("refresh_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    token_data = refresh_tokens_db.get(refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌不存在或已过期"
        )
    
    # 检查刷新令牌是否过期
    if token_data["expires_at"] < time.time():
        # 清理过期令牌
        del refresh_tokens_db[refresh_token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已过期"
        )
    
    username = token_data["username"]
    user = users_db.get(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    # 创建新的访问令牌
    access_token_payload = {
        "sub": username,
        "role": user["role"],
        "name": user["full_name"],
        "iat": int(time.time())
    }
    access_token = jwt_utils.create_token(access_token_payload)
    
    # 可选的：创建新的刷新令牌（轮换）
    new_refresh_token = f"refresh_{int(time.time())}_{username}"
    refresh_tokens_db[new_refresh_token] = {
        "username": username,
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + 7 * 24 * 3600
    }
    
    # 删除旧的刷新令牌
    del refresh_tokens_db[refresh_token]
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800
    )

@app.get("/protected", response_model=ProtectedResponse)
async def protected_endpoint(payload: Dict = Depends(verify_token_dependency)):
    """受保护端点，需要有效的JWT令牌"""
    username = payload.get("sub")
    user = users_db.get(username, {})
    
    expires_at = payload.get("exp", 0)
    expires_time = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d %H:%M:%S")
    
    return ProtectedResponse(
        message="访问成功！",
        user_info={
            "username": username,
            "role": payload.get("role"),
            "name": payload.get("name"),
            "token_expires": expires_time
        },
        token_expires_at=expires_at
    )

@app.get("/status")
async def get_status(request: Request):
    """获取服务状态"""
    auth_header = request.headers.get("Authorization")
    token_count = 0
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = jwt_utils.verify_token(token)
        if payload:
            token_count = 1
    
    return StatusResponse(
        message="JWT认证服务运行正常",
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        token_count=token_count
    )

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "JWT认证服务",
        "endpoints": {
            "POST /login": "登录获取令牌",
            "POST /refresh": "刷新令牌",
            "GET /protected": "受保护端点（需要令牌）",
            "GET /status": "服务状态"
        },
        "jwt_algorithm": "HS256",
        "token_expiry": "30分钟",
        "refresh_token_expiry": "7天"
    }

# 自定义中间件用于演示
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求的中间件"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 错误处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return {
        "detail": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }

# 测试用户端点
@app.get("/users")
async def get_users():
    """获取用户列表（仅用于演示）"""
    return {
        "users": [
            {"username": username, "role": data["role"]}
            for username, data in users_db.items()
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "BE_05_JWTAuthMiddleware:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )