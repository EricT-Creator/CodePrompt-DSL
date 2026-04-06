# MC-BE-04: Token Bucket速率限制器技术方案

## 1. Token Bucket算法细节

### 1.1 算法原理
Token Bucket算法是一种常用的流量整形和速率限制算法，其核心思想是：
- 一个桶以固定速率（rate）产生令牌（tokens）
- 桶有最大容量（burst），超过容量的令牌会被丢弃
- 请求需要消耗令牌才能被处理
- 如果桶中没有足够令牌，请求被拒绝或延迟

### 1.2 数学模型
```
设：
  rate = r 令牌/秒（产生速率）
  burst = b 令牌（桶容量）
  tokens = 当前桶中令牌数
  last_refill = 上次补充时间

补充时间间隔 Δt = 当前时间 - last_refill
补充令牌数 = r × Δt
新令牌数 = min(tokens + r × Δt, b)
```

### 1.3 算法实现
```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
import time

@dataclass
class TokenBucket:
    """Token Bucket实现"""
    rate_per_second: float  # 每秒产生令牌数
    burst_size: int  # 桶容量
    tokens: float = field(default=0.0)  # 当前令牌数
    last_refill_time: float = field(default_factory=time.time)  # 上次补充时间
    
    def refill(self) -> None:
        """补充令牌"""
        current_time = time.time()
        time_passed = current_time - self.last_refill_time
        
        # 计算应补充的令牌数
        new_tokens = time_passed * self.rate_per_second
        self.tokens = min(self.tokens + new_tokens, self.burst_size)
        self.last_refill_time = current_time
    
    def consume(self, tokens_required: float = 1.0) -> bool:
        """
        尝试消费令牌
        
        Args:
            tokens_required: 需要的令牌数
        
        Returns:
            bool: 是否成功消费
        """
        self.refill()
        
        if self.tokens >= tokens_required:
            self.tokens -= tokens_required
            return True
        return False
    
    def get_wait_time(self, tokens_required: float = 1.0) -> float:
        """
        获取需要等待的时间（秒）
        
        Returns:
            float: 需要等待的秒数，如果不需要等待返回0
        """
        self.refill()
        
        if self.tokens >= tokens_required:
            return 0.0
        
        # 计算需要等待的时间
        tokens_needed = tokens_required - self.tokens
        return tokens_needed / self.rate_per_second
```

## 2. 每IP桶管理

### 2.1 IP桶管理器
```python
class IPBucketManager:
    """IP地址桶管理器"""
    
    def __init__(
        self,
        default_rate: float = 10.0,  # 默认10请求/秒
        default_burst: int = 20,  # 默认突发20请求
        cleanup_interval: int = 300  # 清理间隔（秒）
    ):
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.whitelist: set = set()
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    def get_bucket(self, ip_address: str) -> TokenBucket:
        """获取或创建IP的Token Bucket"""
        # 检查白名单
        if ip_address in self.whitelist:
            # 白名单IP使用无限桶
            return UnlimitedBucket()
        
        # 获取现有桶或创建新桶
        if ip_address not in self.buckets:
            self.buckets[ip_address] = TokenBucket(
                rate_per_second=self.default_rate,
                burst_size=self.default_burst
            )
        
        return self.buckets[ip_address]
    
    def set_rate_limit(
        self,
        ip_address: str,
        rate_per_second: float,
        burst_size: int
    ) -> None:
        """为特定IP设置速率限制"""
        if ip_address in self.buckets:
            self.buckets[ip_address].rate_per_second = rate_per_second
            self.buckets[ip_address].burst_size = burst_size
        else:
            self.buckets[ip_address] = TokenBucket(
                rate_per_second=rate_per_second,
                burst_size=burst_size
            )
    
    def add_to_whitelist(self, ip_address: str) -> None:
        """添加IP到白名单"""
        self.whitelist.add(ip_address)
        # 从限制桶中移除
        self.buckets.pop(ip_address, None)
    
    def remove_from_whitelist(self, ip_address: str) -> None:
        """从白名单移除IP"""
        self.whitelist.discard(ip_address)
    
    def cleanup_inactive_buckets(self) -> None:
        """清理不活跃的桶"""
        current_time = time.time()
        
        # 定期清理
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        inactive_ips = []
        for ip, bucket in self.buckets.items():
            # 如果桶长时间未使用（30分钟）且令牌已满，清理
            time_since_last_use = current_time - bucket.last_refill_time
            if time_since_last_use > 1800 and bucket.tokens >= bucket.burst_size:
                inactive_ips.append(ip)
        
        for ip in inactive_ips:
            del self.buckets[ip]
        
        self.last_cleanup = current_time
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_buckets": len(self.buckets),
            "whitelist_size": len(self.whitelist),
            "default_rate": self.default_rate,
            "default_burst": self.default_burst
        }

@dataclass
class UnlimitedBucket:
    """无限桶（用于白名单）"""
    
    def consume(self, tokens_required: float = 1.0) -> bool:
        """总是允许消费"""
        return True
    
    def get_wait_time(self, tokens_required: float = 1.0) -> float:
        """不需要等待"""
        return 0.0
    
    def refill(self) -> None:
        """无需补充"""
        pass
```

### 2.2 IP地址提取
```python
def extract_client_ip(request) -> str:
    """
    从请求中提取客户端IP地址
    
    支持多种头部：
    1. X-Forwarded-For（代理转发）
    2. X-Real-IP
    3. 直接连接IP
    """
    # 尝试从X-Forwarded-For获取
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 取第一个IP（客户端原始IP）
        return forwarded_for.split(",")[0].strip()
    
    # 尝试从X-Real-IP获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 使用直接连接IP
    if hasattr(request, "client") and request.client:
        return request.client[0]  # (host, port) 元组
    
    # 回退到本地IP
    return "127.0.0.1"
```

## 3. 中间件集成

### 3.1 FastAPI中间件实现
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

class TokenBucketMiddleware(BaseHTTPMiddleware):
    """Token Bucket速率限制中间件"""
    
    def __init__(
        self,
        app,
        ip_bucket_manager: IPBucketManager,
        cost_per_request: float = 1.0,
        enabled_paths: Optional[list] = None,
        excluded_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.ip_bucket_manager = ip_bucket_manager
        self.cost_per_request = cost_per_request
        self.enabled_paths = enabled_paths or ["/"]  # 默认所有路径
        self.excluded_paths = excluded_paths or []
    
    async def dispatch(self, request: Request, call_next):
        # 检查是否应跳过此路径
        if self._should_skip_path(request.url.path):
            return await call_next(request)
        
        # 提取客户端IP
        client_ip = extract_client_ip(request)
        
        # 获取Token Bucket
        bucket = self.ip_bucket_manager.get_bucket(client_ip)
        
        # 尝试消费令牌
        if bucket.consume(self.cost_per_request):
            # 令牌足够，处理请求
            response = await call_next(request)
            
            # 添加速率限制头部
            response.headers["X-RateLimit-Limit"] = str(bucket.burst_size)
            response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
            response.headers["X-RateLimit-Reset"] = str(
                int(bucket.last_refill_time + (1 / bucket.rate_per_second))
            )
            
            return response
        else:
            # 令牌不足，计算需要等待的时间
            wait_time = bucket.get_wait_time(self.cost_per_request)
            
            # 返回429 Too Many Requests
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": int(wait_time),
                    "rate_limit": bucket.rate_per_second,
                    "burst_limit": bucket.burst_size
                },
                headers={
                    "Retry-After": str(int(wait_time)),
                    "X-RateLimit-Limit": str(bucket.burst_size),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + wait_time))
                }
            )
    
    def _should_skip_path(self, path: str) -> bool:
        """检查是否应跳过此路径的速率限制"""
        # 检查排除路径
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        
        # 检查启用路径
        if self.enabled_paths == ["/"]:
            return False
        
        for enabled in self.enabled_paths:
            if path.startswith(enabled):
                return False
        
        # 路径不在启用列表中
        return True
```

### 3.2 中间件配置
```python
def create_app() -> FastAPI:
    """创建FastAPI应用并配置中间件"""
    app = FastAPI(title="Token Bucket Rate Limiter API")
    
    # 创建IP桶管理器
    ip_bucket_manager = IPBucketManager(
        default_rate=10.0,  # 10请求/秒
        default_burst=20,   # 突发20请求
        cleanup_interval=300  # 5分钟清理一次
    )
    
    # 添加白名单IP（示例）
    ip_bucket_manager.add_to_whitelist("127.0.0.1")
    ip_bucket_manager.add_to_whitelist("::1")
    
    # 添加中间件
    app.add_middleware(
        TokenBucketMiddleware,
        ip_bucket_manager=ip_bucket_manager,
        cost_per_request=1.0,  # 每个请求消耗1个令牌
        enabled_paths=["/api/"],  # 只对/api/路径启用
        excluded_paths=["/api/docs", "/api/redoc", "/api/openapi.json"]
    )
    
    return app
```

## 4. Retry-After计算

### 4.1 等待时间计算
```python
def calculate_retry_after(bucket: TokenBucket, tokens_required: float = 1.0) -> int:
    """
    计算Retry-After头部值（秒）
    
    Returns:
        int: 需要等待的秒数（向上取整）
    """
    wait_time = bucket.get_wait_time(tokens_required)
    
    # 向上取整到最近的秒数
    retry_after = int(wait_time) + (1 if wait_time % 1 > 0 else 0)
    
    # 确保至少1秒
    return max(1, retry_after)

def format_retry_after_header(retry_after: int) -> str:
    """
    格式化Retry-After头部值
    
    支持两种格式：
    1. 秒数（整数）
    2. HTTP日期时间（RFC 1123）
    """
    # 使用秒数格式（更简单）
    return str(retry_after)
    
    # 或者使用HTTP日期时间格式
    # from datetime import datetime, timedelta
    # retry_time = datetime.utcnow() + timedelta(seconds=retry_after)
    # return retry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
```

### 4.2 错误响应生成
```python
from fastapi.responses import JSONResponse
import time

def create_rate_limit_response(
    bucket: TokenBucket,
    cost_per_request: float = 1.0
) -> JSONResponse:
    """创建速率限制错误响应"""
    # 计算需要等待的时间
    retry_after = calculate_retry_after(bucket, cost_per_request)
    
    # 计算重置时间戳
    reset_timestamp = int(time.time() + retry_after)
    
    # 创建响应
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests",
            "retry_after": retry_after,
            "rate_limit": bucket.rate_per_second,
            "burst_limit": bucket.burst_size,
            "reset_at": reset_timestamp
        },
        headers={
            "Retry-After": format_retry_after_header(retry_after),
            "X-RateLimit-Limit": str(bucket.burst_size),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_timestamp)
        }
    )
```

### 4.3 客户端重试逻辑
```python
def should_retry_request(response) -> bool:
    """检查是否应重试请求"""
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                # 解析Retry-After头部
                wait_seconds = int(retry_after)
                return True, wait_seconds
            except ValueError:
                pass
    
    return False, 0

async def make_request_with_retry(url, max_retries=3):
    """带重试的请求函数"""
    import aiohttp
    
    for attempt in range(max_retries):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 429:
                    should_retry, wait_time = should_retry_request(response)
                    if should_retry and attempt < max_retries - 1:
                        # 等待指定时间后重试
                        await asyncio.sleep(wait_time)
                        continue
                
                return await response.json()
    
    raise Exception("Max retries exceeded")
```

## 5. 约束确认

### 5.1 Python + FastAPI
- 使用FastAPI构建API
- Python类型注解和异步支持

### 5.2 Token Bucket required, no simple counter
- 必须实现Token Bucket算法
- 不使用简单的计数器
- 支持突发流量和持续速率限制

### 5.3 stdlib + fastapi only, no Redis
- 仅使用Python标准库
- 仅使用FastAPI框架
- 不使用Redis或其他外部存储
- 内存中管理Token Bucket

### 5.4 Single file
- 所有代码在单个Python文件中
- 包含Token Bucket实现、中间件和API端点

### 5.5 429 with Retry-After, IP whitelist
- 返回HTTP 429状态码
- 包含Retry-After头部
- 支持IP白名单绕过限制

### 5.6 Code only
- 纯代码实现
- 无外部配置文件
- 自包含速率限制系统