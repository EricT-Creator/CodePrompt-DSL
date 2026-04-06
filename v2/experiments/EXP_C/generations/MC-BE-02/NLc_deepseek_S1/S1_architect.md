# MC-BE-02: FastAPI JWT认证系统技术方案

## 1. JWT结构设计

### 1.1 标准JWT组成
```
JWT = Base64Url(Header) + "." + Base64Url(Payload) + "." + Base64Url(Signature)
```

### 1.2 Header结构
```python
import json
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class JWTHeader:
    def __init__(self):
        self.alg = "HS256"  # HMAC-SHA256算法
        self.typ = "JWT"
    
    def to_dict(self) -> Dict[str, str]:
        return {"alg": self.alg, "typ": self.typ}
    
    def to_base64(self) -> str:
        """将Header转换为Base64Url编码"""
        header_json = json.dumps(self.to_dict(), separators=(',', ':'))
        return base64.urlsafe_b64encode(
            header_json.encode('utf-8')
        ).decode('utf-8').rstrip('=')
```

### 1.3 Payload结构
```python
class JWTPayload:
    def __init__(
        self,
        user_id: str,
        username: str,
        expires_in_minutes: int = 30
    ):
        self.sub = user_id  # subject - 用户ID
        self.username = username  # 用户名
        self.iat = int(datetime.utcnow().timestamp())  # issued at - 签发时间
        self.exp = self.iat + (expires_in_minutes * 60)  # expiration - 过期时间
        self.jti = self._generate_jti()  # JWT ID - 唯一标识符
    
    def _generate_jti(self) -> str:
        """生成唯一的JWT标识符"""
        import uuid
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.sub,
            "username": self.username,
            "iat": self.iat,
            "exp": self.exp,
            "jti": self.jti
        }
    
    def to_base64(self) -> str:
        """将Payload转换为Base64Url编码"""
        payload_json = json.dumps(self.to_dict(), separators=(',', ':'))
        return base64.urlsafe_b64encode(
            payload_json.encode('utf-8')
        ).decode('utf-8').rstrip('=')
```

## 2. HMAC-SHA256签名流程

### 2.1 签名生成
```python
class JWTSigner:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def sign(self, header_b64: str, payload_b64: str) -> str:
        """生成HMAC-SHA256签名"""
        # 创建签名数据
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        
        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            self.secret_key,
            signing_input,
            hashlib.sha256
        ).digest()
        
        # Base64Url编码
        return base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    def verify(self, token: str) -> bool:
        """验证JWT签名"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 重新计算签名
            expected_signature = self.sign(header_b64, payload_b64)
            
            # 比较签名（使用恒定时间比较防止时序攻击）
            return hmac.compare_digest(
                signature_b64,
                expected_signature
            )
        except Exception:
            return False
```

### 2.2 JWT生成完整流程
```python
class JWTManager:
    def __init__(self, secret_key: str):
        self.signer = JWTSigner(secret_key)
    
    def create_token(self, user_id: str, username: str) -> str:
        """创建JWT令牌"""
        # 创建Header和Payload
        header = JWTHeader()
        payload = JWTPayload(user_id, username)
        
        # 获取Base64编码
        header_b64 = header.to_base64()
        payload_b64 = payload.to_base64()
        
        # 生成签名
        signature_b64 = self.signer.sign(header_b64, payload_b64)
        
        # 组合JWT
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码并验证JWT令牌"""
        if not self.signer.verify(token):
            return None
        
        try:
            parts = token.split('.')
            payload_b64 = parts[1]
            
            # 补全Base64填充
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += "=" * padding
            
            # 解码Payload
            payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
            
            # 检查过期时间
            current_time = int(datetime.utcnow().timestamp())
            if payload.get('exp', 0) < current_time:
                return None
            
            return payload
        except Exception:
            return None
```

## 3. 令牌刷新逻辑

### 3.1 刷新令牌设计
```python
class RefreshTokenManager:
    def __init__(self, jwt_manager: JWTManager, refresh_expiry_hours: int = 24):
        self.jwt_manager = jwt_manager
        self.refresh_expiry_hours = refresh_expiry_hours
        self.refresh_tokens: Dict[str, RefreshTokenInfo] = {}
    
    def create_refresh_token(self, user_id: str, username: str) -> str:
        """创建刷新令牌"""
        import uuid
        import hashlib
        
        # 生成唯一刷新令牌
        refresh_token = str(uuid.uuid4())
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # 存储刷新令牌信息
        self.refresh_tokens[token_hash] = RefreshTokenInfo(
            user_id=user_id,
            username=username,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=self.refresh_expiry_hours),
            used=False
        )
        
        return refresh_token
    
    def validate_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """验证刷新令牌并返回用户信息"""
        import hashlib
        
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        if token_hash not in self.refresh_tokens:
            return None
        
        token_info = self.refresh_tokens[token_hash]
        
        # 检查是否已使用
        if token_info.used:
            return None
        
        # 检查是否过期
        if datetime.utcnow() > token_info.expires_at:
            del self.refresh_tokens[token_hash]
            return None
        
        # 标记为已使用（一次性使用）
        token_info.used = True
        
        return {
            "user_id": token_info.user_id,
            "username": token_info.username
        }
```

## 4. 中间件/依赖设计

### 4.1 认证依赖
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """获取当前用户依赖"""
    token = credentials.credentials
    
    # 解码和验证JWT
    payload = jwt_manager.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload
```

### 4.2 端点实现
```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """登录端点 - 验证用户并颁发JWT"""
    # 验证用户凭据（简化示例）
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # 创建访问令牌
    access_token = jwt_manager.create_token(
        user_id=user.id,
        username=user.username
    )
    
    # 创建刷新令牌
    refresh_token = refresh_manager.create_refresh_token(
        user_id=user.id,
        username=user.username
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=30 * 60,  # 30分钟
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """刷新令牌端点"""
    # 验证刷新令牌
    user_info = refresh_manager.validate_refresh_token(refresh_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # 颁发新的访问令牌
    new_access_token = jwt_manager.create_token(
        user_id=user_info["user_id"],
        username=user_info["username"]
    )
    
    # 可选的：颁发新的刷新令牌
    new_refresh_token = refresh_manager.create_refresh_token(
        user_id=user_info["user_id"],
        username=user_info["username"]
    )
    
    return TokenResponse(
        access_token=new_access_token,
        expires_in=30 * 60,
        refresh_token=new_refresh_token
    )

@router.get("/protected")
async def protected_route(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """受保护端点 - 需要有效JWT"""
    return {
        "message": f"Hello {current_user['username']}!",
        "user_id": current_user["sub"],
        "expires_at": current_user["exp"]
    }
```

## 5. 约束确认

### 5.1 Python + FastAPI
- 使用FastAPI构建认证API
- Python类型注解和Pydantic模型

### 5.2 Manual JWT via hmac+base64, no PyJWT
- 手动实现JWT生成和验证
- 使用hmac和hashlib进行签名
- 使用base64进行编码
- 不依赖PyJWT库

### 5.3 stdlib + fastapi + uvicorn only
- 仅使用Python标准库
- FastAPI作为Web框架
- Uvicorn作为服务器
- 无额外依赖

### 5.4 Single file
- 所有代码在单个Python文件中
- 包含JWT管理、刷新令牌和API端点

### 5.5 Endpoints: login, protected, refresh
- `/login` - 用户登录，颁发JWT
- `/protected` - 需要JWT验证的受保护端点
- `/refresh` - 使用刷新令牌获取新访问令牌

### 5.6 Code only
- 纯代码实现
- 无外部配置文件
- 自包含JWT认证系统