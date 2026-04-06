# MC-BE-02: FastAPI JWT认证系统技术方案

## 1. JWT结构设计

### 1.1 JWT三部分结构
```python
# JWT = Header.Payload.Signature
class JWTStructure:
    """
    JWT标准结构:
    - Header: 算法和类型声明 {"alg": "HS256", "typ": "JWT"}
    - Payload: 声明(claims) {"sub": "user123", "exp": 1712345678, ...}
    - Signature: HMAC-SHA256签名
    """
    
    @staticmethod
    def encode(header: dict, payload: dict, secret_key: str) -> str:
        """编码JWT令牌"""
        # 1. Base64Url编码头部
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b'=')
        
        # 2. Base64Url编码载荷
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=')
        
        # 3. 创建签名内容
        signing_input = f"{header_b64.decode()}.{payload_b64.decode()}"
        
        # 4. HMAC-SHA256签名
        signature = hmac.new(
            secret_key.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        
        # 5. Base64Url编码签名
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=')
        
        # 6. 组合完整JWT
        return f"{signing_input}.{signature_b64.decode()}"
```

### 1.2 标准声明字段
```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class JWTClaims:
    """JWT标准声明字段"""
    
    # 标准声明 (RFC 7519)
    issuer: Optional[str] = None          # iss: 签发者
    subject: Optional[str] = None         # sub: 主题 (用户ID)
    audience: Optional[str] = None        # aud: 接收方
    expiration: Optional[datetime] = None # exp: 过期时间
    not_before: Optional[datetime] = None # nbf: 生效时间
    issued_at: Optional[datetime] = None  # iat: 签发时间
    jwt_id: Optional[str] = None          # jti: JWT ID
    
    # 自定义声明
    user_id: Optional[str] = None
    roles: list[str] = None
    permissions: list[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典，处理特殊类型"""
        claims = {}
        
        # 处理标准声明
        if self.issuer:
            claims["iss"] = self.issuer
        if self.subject:
            claims["sub"] = self.subject
        if self.audience:
            claims["aud"] = self.audience
        if self.expiration:
            claims["exp"] = int(self.expiration.timestamp())
        if self.not_before:
            claims["nbf"] = int(self.not_before.timestamp())
        if self.issued_at:
            claims["iat"] = int(self.issued_at.timestamp())
        if self.jwt_id:
            claims["jti"] = self.jwt_id
        
        # 处理自定义声明
        if self.user_id:
            claims["uid"] = self.user_id
        if self.roles:
            claims["roles"] = self.roles
        if self.permissions:
            claims["perms"] = self.permissions
        
        return claims
```

## 2. HMAC-SHA256签名流程

### 2.1 签名生成
```python
class JWTSigner:
    """JWT签名和验证器"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        
        # 验证算法支持
        if algorithm != "HS256":
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def sign(self, header: dict, payload: dict) -> str:
        """生成JWT签名"""
        
        # 1. 验证头部
        if header.get("alg") != self.algorithm:
            raise ValueError("Header algorithm mismatch")
        if header.get("typ") != "JWT":
            raise ValueError("Header type must be 'JWT'")
        
        # 2. 编码头部和载荷
        header_b64 = self._base64url_encode(json.dumps(header))
        payload_b64 = self._base64url_encode(json.dumps(payload))
        
        # 3. 创建签名输入
        signing_input = f"{header_b64}.{payload_b64}"
        
        # 4. HMAC-SHA256签名
        signature = hmac.new(
            self.secret_key.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        
        # 5. 编码签名
        signature_b64 = self._base64url_encode(signature)
        
        # 6. 返回完整JWT
        return f"{signing_input}.{signature_b64}"
    
    def verify(self, token: str) -> tuple[dict, dict]:
        """验证JWT令牌"""
        
        # 1. 分割令牌
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        # 2. 解码头部和载荷
        try:
            header = json.loads(self._base64url_decode(header_b64))
            payload = json.loads(self._base64url_decode(payload_b64))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid token encoding: {e}")
        
        # 3. 验证头部
        if header.get("alg") != self.algorithm:
            raise ValueError("Invalid algorithm")
        
        # 4. 重新计算签名进行验证
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            self.secret_key.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        
        provided_signature = self._base64url_decode(signature_b64)
        
        # 5. 使用常量时间比较防止时序攻击
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise ValueError("Invalid signature")
        
        # 6. 验证声明（过期时间等）
        self._validate_claims(payload)
        
        return header, payload
    
    @staticmethod
    def _base64url_encode(data: Union[str, bytes]) -> str:
        """Base64Url编码"""
        if isinstance(data, str):
            data = data.encode()
        
        encoded = base64.urlsafe_b64encode(data).rstrip(b'=')
        return encoded.decode()
```

### 2.2 Base64Url编码实现
```python
class Base64UrlCodec:
    """Base64Url编解码器"""
    
    @staticmethod
    def encode(data: Union[str, bytes]) -> str:
        """编码为Base64Url字符串"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 标准Base64编码
        encoded = base64.b64encode(data)
        
        # URL安全转换
        url_safe = (
            encoded
            .replace(b'+', b'-')
            .replace(b'/', b'_')
            .rstrip(b'=')
        )
        
        return url_safe.decode('ascii')
    
    @staticmethod
    def decode(encoded: str) -> bytes:
        """解码Base64Url字符串"""
        # 添加填充字符
        padding_needed = 4 - (len(encoded) % 4)
        if padding_needed != 4:
            encoded += '=' * padding_needed
        
        # URL安全转换回标准Base64
        standard = (
            encoded
            .replace('-', '+')
            .replace('_', '/')
        )
        
        return base64.b64decode(standard)
```

## 3. 令牌刷新逻辑

### 3.1 刷新令牌机制
```python
class TokenManager:
    """令牌管理器"""
    
    def __init__(
        self,
        secret_key: str,
        access_token_ttl: int = 900,      # 15分钟
        refresh_token_ttl: int = 604800,  # 7天
        refresh_token_store: dict = None
    ):
        self.signer = JWTSigner(secret_key)
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl
        self.refresh_token_store = refresh_token_store or {}
    
    def create_access_token(self, user_id: str, claims: dict = None) -> str:
        """创建访问令牌"""
        now = datetime.utcnow()
        
        # 标准声明
        jwt_claims = JWTClaims(
            subject=user_id,
            issued_at=now,
            expiration=now + timedelta(seconds=self.access_token_ttl),
            jwt_id=str(uuid.uuid4()),
            user_id=user_id
        )
        
        # 添加自定义声明
        if claims:
            for key, value in claims.items():
                setattr(jwt_claims, key, value)
        
        # 创建令牌
        header = {"alg": "HS256", "typ": "JWT"}
        return self.signer.sign(header, jwt_claims.to_dict())
    
    def create_refresh_token(self, user_id: str) -> tuple[str, str]:
        """创建刷新令牌对 (refresh_token, refresh_token_id)"""
        refresh_token_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # 刷新令牌声明
        claims = JWTClaims(
            subject=user_id,
            issued_at=now,
            expiration=now + timedelta(seconds=self.refresh_token_ttl),
            jwt_id=refresh_token_id,
            user_id=user_id,
            token_type="refresh"
        )
        
        # 生成刷新令牌
        header = {"alg": "HS256", "typ": "JWT"}
        refresh_token = self.signer.sign(header, claims.to_dict())
        
        # 存储刷新令牌信息
        self.refresh_token_store[refresh_token_id] = {
            "user_id": user_id,
            "created_at": now,
            "last_used_at": None,
            "revoked": False
        }
        
        return refresh_token, refresh_token_id
    
    def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """使用刷新令牌获取新的访问令牌"""
        
        try:
            # 验证刷新令牌
            header, payload = self.signer.verify(refresh_token)
            
            # 验证令牌类型
            if payload.get("token_type") != "refresh":
                raise ValueError("Not a refresh token")
            
            # 检查令牌是否被撤销
            token_id = payload.get("jti")
            token_info = self.refresh_token_store.get(token_id)
            
            if not token_info or token_info.get("revoked"):
                raise ValueError("Refresh token revoked")
            
            # 更新最后使用时间
            token_info["last_used_at"] = datetime.utcnow()
            
            # 创建新的访问令牌
            user_id = payload.get("sub")
            new_access_token = self.create_access_token(user_id)
            
            return new_access_token, token_id
            
        except Exception as e:
            raise ValueError(f"Token refresh failed: {e}")
```

### 3.2 令牌撤销机制
```python
class TokenRevocationService:
    """令牌撤销服务"""
    
    def __init__(self, token_store: dict):
        self.token_store = token_store
    
    def revoke_token(self, token_id: str) -> bool:
        """撤销特定令牌"""
        if token_id in self.token_store:
            self.token_store[token_id]["revoked"] = True
            self.token_store[token_id]["revoked_at"] = datetime.utcnow()
            return True
        return False
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """撤销用户所有令牌"""
        revoked_count = 0
        
        for token_id, token_info in self.token_store.items():
            if token_info.get("user_id") == user_id:
                token_info["revoked"] = True
                token_info["revoked_at"] = datetime.utcnow()
                revoked_count += 1
        
        return revoked_count
    
    def is_token_revoked(self, token_id: str) -> bool:
        """检查令牌是否被撤销"""
        token_info = self.token_store.get(token_id)
        return bool(token_info and token_info.get("revoked"))
```

## 4. 中间件/依赖设计

### 4.1 认证依赖注入
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前用户的依赖函数"""
    
    try:
        # 验证JWT令牌
        signer = JWTSigner(SECRET_KEY)
        header, payload = signer.verify(credentials.credentials)
        
        # 返回用户信息
        return {
            "user_id": payload.get("sub"),
            "claims": payload
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

### 4.2 基于角色的权限控制
```python
class RoleChecker:
    """基于角色的权限检查器"""
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        """检查用户是否具有所需角色"""
        
        user_roles = user.get("claims", {}).get("roles", [])
        
        # 检查是否有角色匹配
        if not any(role in self.allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return user

# 使用示例
admin_only = RoleChecker(["admin"])
editor_or_admin = RoleChecker(["editor", "admin"])
```

## 5. 约束确认

### 约束1: Python + FastAPI框架
- 使用FastAPI构建RESTful API
- 利用FastAPI的依赖注入系统
- 集成FastAPI自动文档生成

### 约束2: 手动JWT实现
- 使用hmac和hashlib实现HMAC-SHA256
- 手动处理Base64Url编码
- 不使用PyJWT、python-jose等库

### 约束3: 最小依赖
- 仅使用Python标准库、fastapi和uvicorn
- 不引入其他第三方包
- 所有加密功能基于标准库

### 约束4: 单文件实现
- 所有代码在一个Python文件中
- 包含完整的JWT生成、验证、刷新逻辑
- 提供完整的API端点

### 约束5: 必需端点
- POST /login: 生成访问令牌和刷新令牌
- GET /protected: 验证令牌并返回用户数据
- POST /refresh: 使用刷新令牌获取新访问令牌

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯Python代码
- 无解释性注释

## 6. 安全考虑

1. **密钥管理**: 使用环境变量存储密钥
2. **令牌过期**: 短生命周期访问令牌
3. **刷新令牌轮换**: 每次刷新后使旧令牌失效
4. **HTTPS强制**: 生产环境强制HTTPS
5. **安全头**: 添加安全相关的HTTP头

## 7. 错误处理

1. **令牌验证错误**: 返回401状态码
2. **权限不足**: 返回403状态码
3. **令牌过期**: 明确的过期错误消息
4. **刷新令牌失效**: 引导用户重新登录

---

*文档字数: 约1970字*