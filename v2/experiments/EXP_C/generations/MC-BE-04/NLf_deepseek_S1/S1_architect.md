# MC-BE-04: FastAPI令牌桶速率限制器技术方案

## 1. 令牌桶算法详情

### 1.1 算法核心原理
```python
class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(
        self,
        rate: float,           # 令牌填充速率（令牌/秒）
        capacity: int,         # 桶容量（最大令牌数）
        initial_tokens: int = None
    ):
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """消费指定数量的令牌，返回是否成功"""
        
        # 1. 先补充令牌
        self._refill()
        
        # 2. 检查是否有足够令牌
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def _refill(self):
        """根据时间补充令牌"""
        
        now = time.time()
        time_passed = now - self.last_refill
        
        # 计算应补充的令牌数
        tokens_to_add = time_passed * self.rate
        
        # 补充令牌，不超过容量
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """获取需要等待的时间（秒）"""
        
        # 先补充令牌
        self._refill()
        
        # 计算还需要多少令牌
        tokens_needed = tokens - self.tokens
        
        if tokens_needed <= 0:
            return 0.0
        
        # 计算需要等待的时间
        return tokens_needed / self.rate
```

### 1.2 算法特性
1. **平滑流量**: 允许短时间内的突发流量（最多桶容量）
2. **持续速率限制**: 长期平均速率不超过设定值
3. **低延迟**: 令牌足够时立即通过
4. **公平性**: 基于时间的令牌补充

### 1.3 数学模型
- **令牌补充公式**: `tokens = min(capacity, current_tokens + Δt × rate)`
- **等待时间公式**: `wait_time = max(0, needed_tokens) / rate`
- **突发容量**: 最大突发请求数 = `capacity`

## 2. 每IP桶管理

### 2.1 IP桶管理器
```python
class IPBucketManager:
    """IP地址到令牌桶的映射管理器"""
    
    def __init__(
        self,
        rate_per_ip: float,
        capacity_per_ip: int,
        cleanup_interval: int = 300  # 5分钟清理一次
    ):
        self.rate_per_ip = rate_per_ip
        self.capacity_per_ip = capacity_per_ip
        self.buckets: dict[str, TokenBucket] = {}
        self.last_activity: dict[str, float] = {}
        self.cleanup_interval = cleanup_interval
        
    def get_bucket(self, ip_address: str) -> TokenBucket:
        """获取或创建IP对应的令牌桶"""
        
        if ip_address not in self.buckets:
            self.buckets[ip_address] = TokenBucket(
                rate=self.rate_per_ip,
                capacity=self.capacity_per_ip
            )
        
        # 更新最后活动时间
        self.last_activity[ip_address] = time.time()
        
        return self.buckets[ip_address]
    
    def consume_for_ip(self, ip_address: str, tokens: int = 1) -> tuple[bool, float]:
        """为指定IP消费令牌"""
        
        bucket = self.get_bucket(ip_address)
        success = bucket.consume(tokens)
        
        if not success:
            wait_time = bucket.get_wait_time(tokens)
            return False, wait_time
        
        return True, 0.0
    
    def cleanup_inactive(self):
        """清理不活动的IP桶"""
        
        current_time = time.time()
        inactive_threshold = current_time - self.cleanup_interval
        
        # 找出不活动的IP
        inactive_ips = [
            ip for ip, last_active in self.last_activity.items()
            if last_active < inactive_threshold
        ]
        
        # 清理
        for ip in inactive_ips:
            self.buckets.pop(ip, None)
            self.last_activity.pop(ip, None)
```

### 2.2 IP识别策略
```python
class IPResolver:
    """IP地址解析器，支持代理和负载均衡器"""
    
    @staticmethod
    def resolve_ip(request: Request) -> str:
        """从请求中解析客户端真实IP"""
        
        # 1. 检查X-Forwarded-For头部（代理链）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（客户端原始IP）
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip and client_ip != "unknown":
                return client_ip
        
        # 2. 检查X-Real-IP头部
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and real_ip != "unknown":
            return real_ip
        
        # 3. 使用客户端连接IP
        client_host = request.client.host
        if client_host:
            return client_host
        
        # 4. 回退到0.0.0.0
        return "0.0.0.0"
    
    @staticmethod
    def normalize_ip(ip_address: str) -> str:
        """标准化IP地址"""
        
        # 处理IPv4映射的IPv6地址
        if ip_address.startswith("::ffff:"):
            ip_address = ip_address[7:]
        
        return ip_address.strip()
```

## 3. 中间件集成

### 3.1 速率限制中间件
```python
class RateLimitMiddleware:
    """速率限制中间件"""
    
    def __init__(
        self,
        app: ASGIApp,
        rate_per_ip: float = 10.0,     # 每秒10个请求
        capacity_per_ip: int = 20,      # 突发容量20个请求
        whitelist: set[str] = None,
        enabled: bool = True
    ):
        self.app = app
        self.bucket_manager = IPBucketManager(
            rate_per_ip=rate_per_ip,
            capacity_per_ip=capacity_per_ip
        )
        self.whitelist = whitelist or set()
        self.enabled = enabled
        
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ):
        # 仅处理HTTP请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        
        # 检查是否启用速率限制
        if not self.enabled:
            await self.app(scope, receive, send)
            return
        
        # 解析客户端IP
        client_ip = IPResolver.resolve_ip(request)
        normalized_ip = IPResolver.normalize_ip(client_ip)
        
        # 检查白名单
        if normalized_ip in self.whitelist:
            await self.app(scope, receive, send)
            return
        
        # 尝试消费令牌
        success, wait_time = self.bucket_manager.consume_for_ip(normalized_ip)
        
        if not success:
            # 构建429响应
            response = self._create_rate_limit_response(wait_time)
            await response(scope, receive, send)
            return
        
        # 请求通过，继续处理
        await self.app(scope, receive, send)
```

### 3.2 响应构建器
```python
class RateLimitResponseBuilder:
    """速率限制响应构建器"""
    
    @staticmethod
    def create_rate_limit_response(
        wait_time: float,
        request_id: str = None,
        retry_after_unit: str = "seconds"
    ) -> JSONResponse:
        """创建429 Too Many Requests响应"""
        
        # 计算Retry-After值（向上取整）
        retry_after = math.ceil(wait_time)
        
        # 构建响应头
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": "429",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + retry_after)
        }
        
        # 添加请求ID（如果提供）
        if request_id:
            headers["X-Request-ID"] = request_id
        
        # 响应体
        response_body = {
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Rate limit exceeded. Please try again later.",
                "details": {
                    "retry_after_seconds": retry_after,
                    "wait_time_seconds": wait_time,
                    "retry_after_unit": retry_after_unit
                }
            }
        }
        
        return JSONResponse(
            status_code=429,
            content=response_body,
            headers=headers
        )
```

## 4. Retry-After计算

### 4.1 等待时间计算
```python
class RetryAfterCalculator:
    """Retry-After头部值计算器"""
    
    @staticmethod
    def calculate_retry_after(wait_time_seconds: float) -> str:
        """计算Retry-After头部值"""
        
        # 向上取整到整数秒
        seconds = math.ceil(wait_time_seconds)
        
        # 返回字符串格式
        return str(seconds)
    
    @staticmethod
    def calculate_for_date(target_time: datetime) -> str:
        """基于目标时间计算Retry-After"""
        
        now = datetime.utcnow()
        delta = target_time - now
        
        # 如果已经过期，返回0
        if delta.total_seconds() <= 0:
            return "0"
        
        # 返回秒数
        return str(math.ceil(delta.total_seconds()))
    
    @staticmethod
    def parse_retry_after(value: str) -> float:
        """解析Retry-After值（支持秒数或HTTP日期）"""
        
        try:
            # 尝试解析为秒数
            return float(value)
        except ValueError:
            # 尝试解析为HTTP日期
            try:
                # HTTP日期格式：Sun, 06 Nov 1994 08:49:37 GMT
                date_format = "%a, %d %b %Y %H:%M:%S %Z"
                target_time = datetime.strptime(value, date_format)
                now = datetime.utcnow()
                
                return (target_time - now).total_seconds()
            except Exception:
                # 无法解析，返回默认值
                return 60.0
```

### 4.2 退避策略集成
```python
class RateLimitBackoff:
    """速率限制退避策略"""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        
    def calculate_backoff(self, attempts: int) -> float:
        """计算退避延迟"""
        
        # 指数退避：2^(attempts-1) * base_delay
        delay = self.base_delay * (2 ** (attempts - 1))
        
        # 应用最大值限制
        delay = min(delay, self.max_delay)
        
        # 添加随机抖动
        if self.jitter:
            jitter_amount = random.uniform(0.0, 0.2)  # 0-20%抖动
            delay = delay * (1.0 + jitter_amount)
        
        return delay
    
    def get_retry_headers(
        self,
        attempts: int,
        wait_time: float = None
    ) -> dict:
        """生成重试相关头部"""
        
        if wait_time is not None:
            retry_after = RetryAfterCalculator.calculate_retry_after(wait_time)
        else:
            backoff_delay = self.calculate_backoff(attempts)
            retry_after = RetryAfterCalculator.calculate_retry_after(backoff_delay)
        
        headers = {
            "Retry-After": retry_after,
            "X-RateLimit-Retry-Attempts": str(attempts),
            "X-RateLimit-Retry-Delay": str(backoff_delay)
        }
        
        return headers
```

## 5. 约束确认

### 约束1: Python + FastAPI框架
- 使用FastAPI中间件系统
- 集成到FastAPI应用生命周期
- 支持异步处理

### 约束2: 令牌桶算法实现
- 实现完整的令牌桶算法
- 不使用简单计数器或固定窗口
- 支持突发流量和平滑限流

### 约束3: 最小依赖
- 仅使用Python标准库和fastapi
- 不使用Redis、memcached等外部存储
- 基于内存的桶管理

### 约束4: 单文件实现
- 所有代码在一个Python文件中
- 包含完整的算法实现和中间件
- 提供配置和扩展接口

### 约束5: 完整HTTP 429响应
- 返回429状态码
- 包含Retry-After头部
- 支持IP白名单绕过
- 提供详细的错误信息

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯Python代码
- 无解释性注释

## 6. 系统架构

### 6.1 组件层次
1. **IP解析层**: 提取客户端真实IP
2. **桶管理层**: 管理IP到令牌桶的映射
3. **算法层**: 令牌桶算法的核心实现
4. **中间件层**: 集成到FastAPI请求处理管道
5. **响应层**: 构建429响应和头部

### 6.2 数据流
```
HTTP请求 → IP解析 → 检查白名单 → 获取令牌桶
                                    ↓
令牌消费 → 成功？ → 是 → 继续处理 → 正常响应
              ↓
              否 → 计算等待时间 → 构建429响应
```

### 6.3 并发安全
- **线程安全设计**: 每个IP独立的令牌桶
- **无锁算法**: 基于时间的令牌补充
- **原子操作**: Python的GIL保证基础操作原子性

## 7. 配置选项

### 7.1 基础配置
```python
class RateLimitConfig:
    """速率限制配置"""
    
    def __init__(
        self,
        enabled: bool = True,
        rate_per_ip: float = 10.0,      # 每秒10个请求
        capacity_per_ip: int = 20,      # 突发容量
        whitelist: list[str] = None,
        exclude_paths: list[str] = None,
        include_paths: list[str] = None
    ):
        self.enabled = enabled
        self.rate_per_ip = rate_per_ip
        self.capacity_per_ip = capacity_per_ip
        self.whitelist = set(whitelist or [])
        self.exclude_paths = set(exclude_paths or [])
        self.include_paths = set(include_paths or [])
```

### 7.2 动态配置
- **运行时调整**: 支持动态更新速率限制
- **A/B测试**: 不同用户组不同限制
- **紧急开关**: 可紧急禁用速率限制

## 8. 监控和日志

### 8.1 指标收集
- **请求速率**: 每个IP的请求频率
- **拒绝率**: 429响应比例
- **桶状态**: 令牌桶填充水平
- **等待时间**: 平均等待时间

### 8.2 审计日志
- **IP活动**: 每个IP的活动历史
- **规则触发**: 速率限制规则触发记录
- **异常检测**: 异常流量模式识别

---

*文档字数: 约1980字*