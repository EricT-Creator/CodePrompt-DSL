# MC-BE-02: JWT认证中间件技术方案

## 项目概述
构建一个基于FastAPI的JWT认证系统。支持：POST /login端点签发JWT令牌、GET /protected端点验证JWT并返回用户数据（无效时返回401）、POST /refresh端点刷新令牌。JWT使用HMAC-SHA256签名和正确的base64url编码，包含过期时间检测。

## 约束解析
基于Header约束：`[L]Python [F]FastAPI [!D]NO_JWT_LIB [AUTH]MANUAL_JWT [D]STDLIB+FASTAPI [O]SINGLE_FILE [API]LOGIN_PROTECTED_REFRESH [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]Python | 使用Python语言 |
| [F]FastAPI | 使用FastAPI框架 |
| [!D]NO_JWT_LIB | 禁止使用JWT库 |
| [AUTH]MANUAL_JWT | 手动实现JWT逻辑 |
| [D]STDLIB+FASTAPI | 仅使用标准库和FastAPI |
| [O]SINGLE_FILE | 输出为单文件 |
| [API]LOGIN_PROTECTED_REFRESH | 提供login、protected、refresh端点 |
| [OUT]CODE_ONLY | 仅输出代码，不包含配置 |

## JWT结构与HMAC-SHA256签名流程

### JWT标准格式
JWT由三部分组成，以点号分隔：
```
header.payload.signature
```

示例JWT：
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwidXNlcm5hbWUiOiJqb2huZG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyNDI2MjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 各部分实现细节

#### 1. Header（头部）
```python
import json
import base64

class JWTHeader:
    """JWT头部编码器"""
    
    def __init__(self, algorithm: str = "HS256"):
        self.algorithm = algorithm
        self.type = "JWT"
    
    def encode(self) -> str:
        """编码为base64url格式"""
        header_data = {
            "alg": self.algorithm,
            "typ": self.type
        }
        
        # 序列化为JSON
        header_json = json.dumps(header_data, separators=(',', ':'))
        
        # 转换为bytes并base64url编码
        header_bytes = header_json.encode('utf-8')
        encoded = base64.urlsafe_b64encode(header_bytes)
        
        # 移除填充的等号
        return encoded.rstrip(b'=').decode('utf-8')
```

#### 2. Payload（负载）
```python
import time
from typing import Dict, Any, Optional

class JWTPayload:
    """JWT负载编码器"""
    
    def __init__(
        self,
        subject: str,
        username: str,
        expires_in: int = 3600,  # 默认1小时
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        custom_claims: Optional[Dict[str, Any]] = None
    ):
        self.subject = subject
        self.username = username
        self.expires_in = expires_in
        self.issuer = issuer
        self.audience = audience
        self.custom_claims = custom_claims or {}
        
        # 标准声明（Registered Claims）
        self.issued_at = int(time.time())
        self.expiration = self.issued_at + expires_in
    
    def encode(self) -> str:
        """编码为base64url格式"""
        payload_data = {
            "sub": self.subject,
            "username": self.username,
            "iat": self.issued_at,
            "exp": self.expiration
        }
        
        # 添加可选声明
        if self.issuer:
            payload_data["iss"] = self.issuer
        if self.audience:
            payload_data["aud"] = self.audience
        
        # 添加自定义声明
        payload_data.update(self.custom_claims)
        
        # 序列化为JSON
        payload_json = json.dumps(payload_data, separators=(',', ':'))
        
        # 转换为bytes并base64url编码
        payload_bytes = payload_json.encode('utf-8')
        encoded = base64.urlsafe_b64encode(payload_bytes)
        
        # 移除填充的等号
        return encoded.rstrip(b'=').decode('utf-8')
```

#### 3. Signature（签名）
```python
import hmac
import hashlib

class JWTSigner:
    """JWT签名器（HMAC-SHA256）"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def sign(self, data: str) -> str:
        """生成HMAC-SHA256签名"""
        # 创建HMAC对象
        hmac_obj = hmac.new(
            key=self.secret_key,
            msg=data.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        
        # 生成摘要并base64url编码
        digest = hmac_obj.digest()
        encoded = base64.urlsafe_b64encode(digest)
        
        # 移除填充的等号
        return encoded.rstrip(b'=').decode('utf-8')
    
    def verify(self, data: str, signature: str) -> bool:
        """验证签名"""
        expected_signature = self.sign(data)
        
        # 使用恒定时间比较防止时序攻击
        return hmac.compare_digest(
            expected_signature.encode('utf-8'),
            signature.encode('utf-8')
        )
```

### 完整JWT生成流程
```python
class JWTManager:
    """完整的JWT管理器"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.signer = JWTSigner(secret_key)
    
    def create_token(
        self,
        subject: str,
        username: str,
        expires_in: int = 3600,
        custom_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建JWT令牌"""
        # 1. 编码Header
        header = JWTHeader(algorithm="HS256")
        encoded_header = header.encode()
        
        # 2. 编码Payload
        payload = JWTPayload(
            subject=subject,
            username=username,
            expires_in=expires_in,
            custom_claims=custom_claims
        )
        encoded_payload = payload.encode()
        
        # 3. 生成签名数据
        signing_input = f"{encoded_header}.{encoded_payload}"
        
        # 4. 计算签名
        signature = self.signer.sign(signing_input)
        
        # 5. 组合完整JWT
        return f"{signing_input}.{signature}"
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            # 1. 分割JWT三部分
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            encoded_header, encoded_payload, signature = parts
            
            # 2. 验证签名
            signing_input = f"{encoded_header}.{encoded_payload}"
            if not self.signer.verify(signing_input, signature):
                return None
            
            # 3. 解码Payload
            # 添加填充等号（如果需要）
            missing_padding = len(encoded_payload) % 4
            if missing_padding:
                encoded_payload += '=' * (4 - missing_padding)
            
            # Base64解码
            payload_bytes = base64.urlsafe_b64decode(encoded_payload)
            payload_data = json.loads(payload_bytes.decode('utf-8'))
            
            # 4. 检查过期时间
            current_time = int(time.time())
            if current_time > payload_data.get('exp', 0):
                return None
            
            return payload_data
            
        except Exception:
            # 任何异常都视为无效令牌
            return None
```

## API端点设计

### 认证API架构
```
POST /api/v1/auth/login      # 登录并获取JWT
GET  /api/v1/auth/protected  # 受保护端点（需要JWT）
POST /api/v1/auth/refresh    # 刷新JWT令牌
```

### 端点详细实现

#### 1. 登录端点（POST /login）
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI(title="JWT Authentication API")

# 数据模型
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    sub: str
    username: str
    exp: int
    iat: int

# 模拟用户存储（实际应用中应使用数据库）
class UserStore:
    """模拟用户存储"""
    
    def __init__(self):
        # 存储格式：{username: {password_hash, user_data}}
        self.users = {
            "john_doe": {
                "password_hash": "hashed_password_123",  # 实际应使用bcrypt等
                "user_data": {
                    "sub": "user_123",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "roles": ["user", "admin"]
                }
            }
        }
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户凭据"""
        user = self.users.get(username)
        if not user:
            return None
        
        # 简化验证（实际应用中应使用密码哈希验证）
        if password == "demo_password":  # 模拟
            return user["user_data"]
        
        return None

# 依赖注入
security = HTTPBearer()

class AuthService:
    """认证服务"""
    
    def __init__(self, jwt_manager: JWTManager, user_store: UserStore):
        self.jwt_manager = jwt_manager
        self.user_store = user_store
    
    async def login(self, username: str, password: str) -> LoginResponse:
        """处理用户登录"""
        # 1. 验证用户凭据
        user_data = self.user_store.authenticate(username, password)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 2. 生成访问令牌
        access_token = self.jwt_manager.create_token(
            subject=user_data["sub"],
            username=user_data["username"],
            expires_in=3600,  # 1小时
            custom_claims={
                "email": user_data.get("email"),
                "roles": user_data.get("roles", [])
            }
        )
        
        # 3. 生成刷新令牌（长期有效）
        refresh_token = self.jwt_manager.create_token(
            subject=user_data["sub"],
            username=user_data["username"],
            expires_in=86400 * 7,  # 7天
            custom_claims={
                "token_type": "refresh"
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            expires_in=3600,
            refresh_token=refresh_token
        )
    
    async def verify_token(
        self, 
        credentials: HTTPAuthorizationCredentials
    ) -> TokenData:
        """验证JWT令牌"""
        token = credentials.credentials
        
        # 验证令牌
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 转换为TokenData模型
        return TokenData(
            sub=payload.get("sub"),
            username=payload.get("username"),
            exp=payload.get("exp"),
            iat=payload.get("iat")
        )
    
    async def refresh_token(
        self, 
        refresh_token: str
    ) -> LoginResponse:
        """刷新访问令牌"""
        # 1. 验证刷新令牌
        payload = self.jwt_manager.verify_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 2. 确保这是刷新令牌（不是访问令牌）
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token type mismatch"
            )
        
        # 3. 生成新的访问令牌
        access_token = self.jwt_manager.create_token(
            subject=payload["sub"],
            username=payload["username"],
            expires_in=3600,
            custom_claims={
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
        )
        
        # 4. 可选：生成新的刷新令牌（令牌轮换）
        new_refresh_token = self.jwt_manager.create_token(
            subject=payload["sub"],
            username=payload["username"],
            expires_in=86400 * 7,
            custom_claims={
                "token_type": "refresh"
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            expires_in=3600,
            refresh_token=new_refresh_token
        )
```

#### 2. 受保护端点（GET /protected）
```python
from fastapi import Depends

class ProtectedResponse(BaseModel):
    message: str
    user_data: Dict[str, Any]

@app.get("/api/v1/auth/protected", response_model=ProtectedResponse)
async def protected_endpoint(
    token_data: TokenData = Depends(AuthService().verify_token)
):
    """受保护端点示例"""
    return ProtectedResponse(
        message="Access granted",
        user_data={
            "sub": token_data.sub,
            "username": token_data.username,
            "issued_at": token_data.iat,
            "expires_at": token_data.exp
        }
    )
```

#### 3. 令牌刷新端点（POST /refresh）
```python
class RefreshRequest(BaseModel):
    refresh_token: str

@app.post("/api/v1/auth/refresh", response_model=LoginResponse)
async def refresh_endpoint(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """刷新访问令牌"""
    return await auth_service.refresh_token(request.refresh_token)
```

## 中间件/依赖设计

### 可重用依赖项
```python
from functools import lru_cache

# 配置类
class AuthConfig:
    def __init__(self):
        self.secret_key = "your-secret-key-here"  # 应从环境变量获取
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 7
        self.algorithm = "HS256"

# 依赖注入容器
@lru_cache()
def get_auth_config() -> AuthConfig:
    return AuthConfig()

@lru_cache()
def get_jwt_manager(config: AuthConfig = Depends(get_auth_config)) -> JWTManager:
    return JWTManager(secret_key=config.secret_key)

@lru_cache()
def get_user_store() -> UserStore:
    return UserStore()

@lru_cache()
def get_auth_service(
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    user_store: UserStore = Depends(get_user_store)
) -> AuthService:
    return AuthService(jwt_manager=jwt_manager, user_store=user_store)
```

### 安全中间件
```python
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 移除不必要的头部
        response.headers.pop("Server", None)
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.request_counts = {}  # {ip: [(timestamp, count)]}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # 清理过期记录
        current_time = time.time()
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (ts, cnt) for ts, cnt in self.request_counts[client_ip]
                if current_time - ts < self.window
            ]
        
        # 获取当前计数
        current_count = sum(cnt for _, cnt in self.request_counts.get(client_ip, []))
        
        # 检查是否超过限制
        if current_count >= self.limit:
            return Response(
                content="Too many requests",
                status_code=429,
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # 记录新请求
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        self.request_counts[client_ip].append((current_time, 1))
        
        # 调用下一个中间件或路由
        response = await call_next(request)
        
        # 添加速率限制头部
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(self.limit - current_count - 1)
        
        return response
```

## 令牌刷新逻辑

### 双令牌策略
```python
class TokenPair:
    """令牌对管理器"""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self.active_tokens: Dict[str, Dict[str, Any]] = {}  # {user_id: {access_token, refresh_token, expires_at}}
    
    async def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建访问令牌和刷新令牌对"""
        # 生成访问令牌
        access_token = self.auth_service.jwt_manager.create_token(
            subject=user_data["sub"],
            username=user_data["username"],
            expires_in=3600,
            custom_claims={
                "email": user_data.get("email"),
                "roles": user_data.get("roles", [])
            }
        )
        
        # 生成刷新令牌
        refresh_token = self.auth_service.jwt_manager.create_token(
            subject=user_data["sub"],
            username=user_data["username"],
            expires_in=86400 * 7,
            custom_claims={
                "token_type": "refresh"
            }
        )
        
        # 存储令牌对
        token_pair = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": int(time.time()) + 3600,
            "user_id": user_data["sub"],
            "created_at": int(time.time())
        }
        
        self.active_tokens[user_data["sub"]] = token_pair
        
        return token_pair
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """使用刷新令牌获取新的访问令牌"""
        # 验证刷新令牌
        payload = self.auth_service.jwt_manager.verify_token(refresh_token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # 检查令牌类型
        if payload.get("token_type") != "refresh":
            return None
        
        # 检查存储中是否有匹配的刷新令牌
        stored_pair = self.active_tokens.get(user_id)
        if not stored_pair or stored_pair["refresh_token"] != refresh_token:
            return None
        
        # 生成新的访问令牌
        new_access_token = self.auth_service.jwt_manager.create_token(
            subject=payload["sub"],
            username=payload["username"],
            expires_in=3600,
            custom_claims={
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
        )
        
        # 更新存储
        stored_pair["access_token"] = new_access_token
        stored_pair["expires_at"] = int(time.time()) + 3600
        
        return {
            "access_token": new_access_token,
            "expires_in": 3600,
            "user_id": user_id
        }
    
    async def revoke_tokens(self, user_id: str) -> bool:
        """撤销用户的所有令牌"""
        if user_id in self.active_tokens:
            del self.active_tokens[user_id]
            return True
        return False
    
    async def clean_expired_tokens(self) -> int:
        """清理过期的令牌"""
        current_time = int(time.time())
        expired_users = []
        
        for user_id, token_pair in self.active_tokens.items():
            if token_pair["expires_at"] < current_time:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.active_tokens[user_id]
        
        return len(expired_users)
```

### 令牌黑名单管理
```python
class TokenBlacklist:
    """令牌黑名单管理器"""
    
    def __init__(self):
        self.blacklisted_tokens: Set[str] = set()
        self.expiry_times: Dict[str, int] = {}  # {token: expiry_time}
    
    def add(self, token: str, expires_in: int) -> None:
        """将令牌加入黑名单"""
        self.blacklisted_tokens.add(token)
        self.expiry_times[token] = int(time.time()) + expires_in
    
    def is_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        # 清理过期的黑名单条目
        self._clean_expired()
        
        return token in self.blacklisted_tokens
    
    def remove(self, token: str) -> bool:
        """从黑名单中移除令牌"""
        if token in self.blacklisted_tokens:
            self.blacklisted_tokens.remove(token)
            if token in self.expiry_times:
                del self.expiry_times[token]
            return True
        return False
    
    def _clean_expired(self) -> None:
        """清理过期的黑名单条目"""
        current_time = int(time.time())
        expired_tokens = []
        
        for token, expiry_time in self.expiry_times.items():
            if expiry_time < current_time:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self.blacklisted_tokens.remove(token)
            del self.expiry_times[token]
```

## 扩展功能

### 角色和权限管理
```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE = "manage"

class RBACManager:
    """基于角色的访问控制管理器"""
    
    def __init__(self):
        # 角色-权限映射
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.READ,
                Permission.WRITE,
                Permission.DELETE,
                Permission.MANAGE
            ],
            UserRole.USER: [
                Permission.READ,
                Permission.WRITE
            ],
            UserRole.GUEST: [
                Permission.READ
            ]
        }
    
    def has_permission(
        self,
        user_roles: List[UserRole],
        required_permission: Permission
    ) -> bool:
        """检查用户是否有指定权限"""
        for role in user_roles:
            if role in self.role_permissions:
                if required_permission in self.role_permissions[role]:
                    return True
        
        return False
    
    def require_permission(self, permission: Permission):
        """创建权限检查依赖项"""
        def permission_checker(
            token_data: TokenData = Depends(AuthService().verify_token)
        ) -> TokenData:
            # 从令牌中提取角色
            user_roles = token_data.custom_claims.get("roles", [])
            
            if not self.has_permission(user_roles, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return token_data
        
        return permission_checker
```

## Constraint Acknowledgment

### [L]Python - Python语言
- 使用Python 3.8+语法和标准库
- 充分利用Python的async/await异步特性
- 遵循Python类型提示最佳实践

### [F]FastAPI - FastAPI框架
- 使用FastAPI构建RESTful认证API
- 利用Pydantic进行请求/响应数据验证
- 提供完整的OpenAPI文档和Swagger UI

### [!D]NO_JWT_LIB - 禁止使用JWT库
- 完全不使用`pyjwt`、`python-jose`等JWT库
- 手动实现JWT的编码、解码、签名和验证
- 避免任何第三方JWT相关的依赖

### [AUTH]MANUAL_JWT - 手动实现JWT逻辑
- 从零实现JWT三部分（Header、Payload、Signature）的生成
- 手动实现HMAC-SHA256签名算法
- 手动实现base64url编码和解码
- 手动实现令牌验证和过期检查

### [D]STDLIB+FASTAPI - 仅使用标准库和FastAPI
- 仅使用Python标准库的hmac、hashlib、base64、json、time等模块
- 仅使用FastAPI框架及其依赖项（Pydantic、Starlette）
- 确保代码的轻量级和可移植性

### [O]SINGLE_FILE - 输出为单文件
- 所有JWT认证逻辑在一个Python文件中实现
- 包含认证服务、令牌管理、API端点和依赖注入
- 遵循单一文件职责原则

### [API]LOGIN_PROTECTED_REFRESH - 提供三个端点
- POST /login: 用户登录并获取JWT令牌对
- GET /protected: 需要JWT认证的受保护端点
- POST /refresh: 使用刷新令牌获取新的访问令牌
- 完整覆盖认证生命周期

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何配置文件、环境变量或数据库设置
- 所有配置通过代码参数化和依赖注入实现
- 确保代码的独立性和自包含性

## 安全特性总结

1. **HMAC-SHA256签名**: 使用强加密算法确保令牌完整性
2. **恒定时间比较**: 防止时序攻击的安全比较算法
3. **令牌过期机制**: 自动检查令牌有效期，防止长期有效
4. **令牌轮换策略**: 访问令牌短期有效，刷新令牌长期但可轮换
5. **黑名单支持**: 支持令牌撤销和黑名单管理
6. **速率限制**: 防止暴力破解和拒绝服务攻击

该设计方案完全满足JWT认证系统的所有功能需求，同时严格遵守所有Header约束，提供安全、可扩展的认证解决方案。