#!/usr/bin/env python3
"""
JWT认证中间件 - 使用FastAPI实现
使用HMAC-SHA256手动签名，仅使用标准库
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# 数据模型
class UserCredentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数


class ProtectedResponse(BaseModel):
    message: str
    user_info: Dict
    token_info: Dict


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# JWT配置
class JWTConfig:
    SECRET_KEY = "your-256-bit-secret-key-change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7


# JWT工具类
class JWTUtils:
    @staticmethod
    def base64url_encode(data: bytes) -> str:
        """Base64 URL安全的编码"""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    @staticmethod
    def base64url_decode(data: str) -> bytes:
        """Base64 URL安全的解码"""
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data.encode('utf-8'))
    
    @staticmethod
    def create_signature(header: str, payload: str, secret: str) -> str:
        """创建HMAC-SHA256签名"""
        message = f"{header}.{payload}".encode('utf-8')
        secret_bytes = secret.encode('utf-8')
        signature = hmac.new(secret_bytes, message, hashlib.sha256).digest()
        return JWTUtils.base64url_encode(signature)
    
    @staticmethod
    def create_token(user_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Header
        header = {
            "alg": JWTConfig.ALGORITHM,
            "typ": "JWT"
        }
        header_b64 = JWTUtils.base64url_encode(json.dumps(header).encode('utf-8'))
        
        # Payload
        payload = {
            "sub": user_id,
            "username": username,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "jti": hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()[:16]
        }
        payload_b64 = JWTUtils.base64url_encode(json.dumps(payload).encode('utf-8'))
        
        # Signature
        signature = JWTUtils.create_signature(header_b64, payload_b64, JWTConfig.SECRET_KEY)
        
        return f"{header_b64}.{payload_b64}.{signature}"
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[Dict]]:
        """验证JWT令牌"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None
            
            header_b64, payload_b64, signature = parts
            
            # 验证签名
            expected_signature = JWTUtils.create_signature(header_b64, payload_b64, JWTConfig.SECRET_KEY)
            if not hmac.compare_digest(signature, expected_signature):
                return False, None
            
            # 解码payload
            payload_json = JWTUtils.base64url_decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
            
            # 检查过期时间
            exp = payload.get('exp')
            if not exp or datetime.utcnow().timestamp() > exp:
                return False, None
            
            return True, payload
            
        except Exception:
            return False, None
    
    @staticmethod
    def create_refresh_token(user_id: str, username: str) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        
        header = {
            "alg": JWTConfig.ALGORITHM,
            "typ": "JWT",
            "rt": "true"  # 标记为刷新令牌
        }
        header_b64 = JWTUtils.base64url_encode(json.dumps(header).encode('utf-8'))
        
        payload = {
            "sub": user_id,
            "username": username,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "type": "refresh"
        }
        payload_b64 = JWTUtils.base64url_encode(json.dumps(payload).encode('utf-8'))
        
        signature = JWTUtils.create_signature(header_b64, payload_b64, JWTConfig.SECRET_KEY)
        
        return f"{header_b64}.{payload_b64}.{signature}"


# 模拟用户数据库
class UserDatabase:
    # 模拟用户数据
    _users = {
        "user1": {
            "id": "1",
            "username": "user1",
            "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
            "email": "user1@example.com",
            "role": "user"
        },
        "user2": {
            "id": "2",
            "username": "user2",
            "password_hash": hashlib.sha256("securepass".encode()).hexdigest(),
            "email": "user2@example.com",
            "role": "admin"
        }
    }
    
    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[Dict]:
        """验证用户凭据"""
        user = cls._users.get(username)
        if not user:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] == password_hash:
            return user
        return None
    
    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[Dict]:
        """根据ID获取用户"""
        for user in cls._users.values():
            if user["id"] == user_id:
                return user
        return None


# 认证依赖
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    token = credentials.credentials
    
    valid, payload = JWTUtils.verify_token(token)
    if not valid or not payload:
        raise HTTPException(
            status_code=401,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get('sub')
    user = UserDatabase.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_active_user(current_user: Dict = Depends(get_current_user)):
    """获取当前活跃用户"""
    # 这里可以添加额外的活跃状态检查
    return current_user


# 速率限制中间件（简单的令牌桶算法）
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
        self.window = 60  # 秒
        
    def refill_tokens(self):
        """补充令牌"""
        now = time.time()
        time_passed = now - self.last_refill
        
        if time_passed > self.window:
            self.tokens = self.requests_per_minute
            self.last_refill = now
        else:
            new_tokens = (time_passed / self.window) * self.requests_per_minute
            self.tokens = min(self.requests_per_minute, self.tokens + new_tokens)
            self.last_refill = now
    
    def consume_token(self) -> bool:
        """消费一个令牌"""
        self.refill_tokens()
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# 创建应用
app = FastAPI(
    title="JWT认证中间件",
    description="使用HMAC-SHA256手动签名的JWT认证系统",
    version="1.0.0"
)

# 全局速率限制器
rate_limiter = RateLimiter(requests_per_minute=100)

# 全局请求计数器
request_counter = {"total": 0, "authenticated": 0}


# 中间件：速率限制和请求统计
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """全局速率限制中间件"""
    request_counter["total"] += 1
    
    # 检查速率限制
    if not rate_limiter.consume_token():
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": "60"}
        )
    
    # 处理请求
    response = await call_next(request)
    
    # 添加请求统计头部
    response.headers["X-Request-Count"] = str(request_counter["total"])
    response.headers["X-Authenticated-Count"] = str(request_counter["authenticated"])
    
    return response


# 路由
@app.post("/login", response_model=TokenResponse)
async def login(credentials: UserCredentials):
    """登录接口，返回JWT令牌"""
    user = UserDatabase.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 创建访问令牌
    access_token = JWTUtils.create_token(
        user_id=user["id"],
        username=user["username"]
    )
    
    # 创建刷新令牌（实际应用中可能单独存储）
    refresh_token = JWTUtils.create_refresh_token(
        user_id=user["id"],
        username=user["username"]
    )
    
    # 更新认证计数器
    request_counter["authenticated"] += 1
    
    return TokenResponse(
        access_token=access_token,
        expires_in=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(current_user: Dict = Depends(get_current_active_user)):
    """受保护的路由，需要JWT认证"""
    # 解析令牌信息
    _, payload = JWTUtils.verify_token(current_user.get("current_token", ""))
    
    token_info = {
        "issued_at": payload.get("iat") if payload else None,
        "expires_at": payload.get("exp") if payload else None,
        "token_id": payload.get("jti") if payload else None
    }
    
    return ProtectedResponse(
        message=f"欢迎回来，{current_user['username']}!",
        user_info={
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "role": current_user["role"]
        },
        token_info=token_info
    )


@app.post("/refresh")
async def refresh_token(request: TokenRefreshRequest):
    """刷新访问令牌"""
    valid, payload = JWTUtils.verify_token(request.refresh_token)
    
    if not valid or not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get('sub')
    username = payload.get('username')
    
    user = UserDatabase.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 创建新的访问令牌
    new_access_token = JWTUtils.create_token(user_id, username)
    
    # 创建新的刷新令牌（轮换）
    new_refresh_token = JWTUtils.create_refresh_token(user_id, username)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@app.get("/status")
async def get_status():
    """获取服务状态和统计信息"""
    tokens_remaining = rate_limiter.tokens
    
    return {
        "status": "running",
        "uptime": time.time() - rate_limiter.last_refill,
        "rate_limit": {
            "requests_per_minute": rate_limiter.requests_per_minute,
            "tokens_remaining": tokens_remaining,
            "window_seconds": rate_limiter.window
        },
        "statistics": {
            "total_requests": request_counter["total"],
            "authenticated_requests": request_counter["authenticated"],
            "anonymous_requests": request_counter["total"] - request_counter["authenticated"]
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """根路由，返回API信息"""
    return {
        "message": "JWT认证中间件API",
        "endpoints": [
            {"path": "/login", "method": "POST", "description": "用户登录，获取JWT令牌"},
            {"path": "/protected", "method": "GET", "description": "需要JWT认证的受保护路由"},
            {"path": "/refresh", "method": "POST", "description": "使用刷新令牌获取新的访问令牌"},
            {"path": "/status", "method": "GET", "description": "获取服务状态和统计信息"},
            {"path": "/docs", "method": "GET", "description": "API文档（Swagger UI）"},
            {"path": "/redoc", "method": "GET", "description": "API文档（ReDoc）"}
        ],
        "jwt_config": {
            "algorithm": JWTConfig.ALGORITHM,
            "access_token_expire_minutes": JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS
        }
    }


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# 演示用户
@app.get("/demo-users")
async def get_demo_users():
    """获取演示用户信息（仅用于测试）"""
    return {
        "users": [
            {
                "username": "user1",
                "password": "password123",
                "role": "user"
            },
            {
                "username": "user2",
                "password": "securepass",
                "role": "admin"
            }
        ],
        "note": "仅用于演示和测试目的"
    }


# 运行应用
if __name__ == "__main__":
    import uvicorn
    
    print("启动JWT认证中间件服务...")
    print(f"访问地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print("\n演示用户:")
    print("- 用户1: user1 / password123")
    print("- 用户2: user2 / securepass")
    print("\n接口说明:")
    print("1. POST /login - 登录获取JWT令牌")
    print("2. GET /protected - 需要Bearer令牌的受保护路由")
    print("3. POST /refresh - 刷新访问令牌")
    print("4. GET /status - 服务状态和统计")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)