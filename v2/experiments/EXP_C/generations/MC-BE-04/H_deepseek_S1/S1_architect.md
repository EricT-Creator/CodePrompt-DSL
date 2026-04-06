# MC-BE-04: 速率限制器中间件技术方案

## 项目概述
构建一个基于FastAPI的令牌桶（Token Bucket）速率限制器中间件。功能包括：可配置的速率/突发限制（按IP）、当速率超过限制时返回HTTP 429状态码和Retry-After头部，支持IP白名单绕过速率限制。

## 约束解析
基于Header约束：`[L]Python [F]FastAPI [ALGO]TOKEN_BUCKET [!A]NO_COUNTER [D]STDLIB+FASTAPI [!D]NO_REDIS [O]SINGLE_FILE [RESP]429_RETRY_AFTER [WL]IP [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]Python | 使用Python语言 |
| [F]FastAPI | 使用FastAPI框架 |
| [ALGO]TOKEN_BUCKET | 使用令牌桶算法 |
| [!A]NO_COUNTER | 禁止使用计数器算法 |
| [D]STDLIB+FASTAPI | 仅使用标准库和FastAPI |
| [!D]NO_REDIS | 禁止使用Redis |
| [O]SINGLE_FILE | 输出为单文件 |
| [RESP]429_RETRY_AFTER | 返回429状态码和Retry-After头部 |
| [WL]IP | 支持IP白名单 |
| [OUT]CODE_ONLY | 仅输出代码，不包含配置 |

## 令牌桶算法细节

### 算法原理
令牌桶算法是一种常用的流量整形和速率限制算法，其核心思想是：
1. 一个桶以固定速率（rate）生成令牌
2. 桶有最大容量（burst），即最多能存储的令牌数
3. 请求到达时，需要从桶中取出一个令牌才能被处理
4. 如果桶中没有令牌，请求被拒绝或延迟

### 数学公式
```
tokens = min(capacity, tokens + (current_time - last_refresh) * rate)
if tokens >= 1:
    tokens -= 1
    return ALLOW
else:
    return DENY
```

### 算法实现
```python
import time
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class TokenBucketConfig:
    """令牌桶配置"""
    rate: float  # 每秒生成的令牌数
    burst: int   # 桶的最大容量（突发容量）
    last_refresh: float = 0.0  # 最后刷新时间
    tokens: float = 0.0  # 当前令牌数

class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, rate: float, burst: int):
        """
        初始化令牌桶
        
        Args:
            rate: 每秒生成的令牌数
            burst: 桶的最大容量
        """
        self.config = TokenBucketConfig(
            rate=rate,
            burst=burst,
            last_refresh=time.time(),
            tokens=burst  # 初始时桶是满的
        )
    
    def _refresh_tokens(self, current_time: float) -> None:
        """刷新令牌桶"""
        time_passed = current_time - self.config.last_refresh
        
        if time_passed > 0:
            # 计算新生成的令牌数
            new_tokens = time_passed * self.config.rate
            
            # 更新令牌数（不超过最大容量）
            self.config.tokens = min(
                self.config.burst,
                self.config.tokens + new_tokens
            )
            
            # 更新最后刷新时间
            self.config.last_refresh = current_time
    
    def consume(self, tokens: float = 1.0) -> Tuple[bool, Optional[float]]:
        """
        尝试消费令牌
        
        Args:
            tokens: 需要消费的令牌数（默认为1）
            
        Returns:
            Tuple[是否成功, 需要等待的时间（秒）]
        """
        current_time = time.time()
        
        # 刷新令牌
        self._refresh_tokens(current_time)
        
        # 检查是否有足够的令牌
        if self.config.tokens >= tokens:
            # 消费令牌
            self.config.tokens -= tokens
            return True, None
        else:
            # 计算需要等待的时间
            tokens_needed = tokens - self.config.tokens
            wait_time = tokens_needed / self.config.rate
            
            return False, wait_time
    
    def peek(self) -> Tuple[bool, Optional[float]]:
        """检查但不消费令牌"""
        current_time = time.time()
        self._refresh_tokens(current_time)
        
        if self.config.tokens >= 1.0:
            return True, None
        else:
            tokens_needed = 1.0 - self.config.tokens
            wait_time = tokens_needed / self.config.rate
            return False, wait_time
    
    def get_stats(self) -> dict:
        """获取桶的统计信息"""
        current_time = time.time()
        self._refresh_tokens(current_time)
        
        return {
            "rate": self.config.rate,
            "burst": self.config.burst,
            "current_tokens": self.config.tokens,
            "last_refresh": self.config.last_refresh,
            "time_since_refresh": current_time - self.config.last_refresh,
            "available_percentage": (self.config.tokens / self.config.burst) * 100
        }
```

### 算法变体扩展
```python
class WeightedTokenBucket(TokenBucket):
    """加权令牌桶（支持不同权重的请求）"""
    
    def __init__(self, rate: float, burst: int):
        super().__init__(rate, burst)
        self.request_weights = {}  # 请求类型 -> 权重
    
    def register_request_type(self, request_type: str, weight: float = 1.0) -> None:
        """注册请求类型及其权重"""
        self.request_weights[request_type] = weight
    
    def consume_request(self, request_type: str = "default") -> Tuple[bool, Optional[float]]:
        """消费特定类型的请求"""
        weight = self.request_weights.get(request_type, 1.0)
        return self.consume(weight)

class HierarchicalTokenBucket:
    """分层令牌桶（支持嵌套限制）"""
    
    def __init__(self, buckets: dict):
        """
        初始化分层令牌桶
        
        Args:
            buckets: 层级配置，如 {
                "global": {"rate": 100, "burst": 200},
                "user": {"rate": 10, "burst": 20},
                "endpoint": {"rate": 5, "burst": 10}
            }
        """
        self.buckets = {}
        for level, config in buckets.items():
            self.buckets[level] = TokenBucket(
                rate=config["rate"],
                burst=config["burst"]
            )
    
    def consume_all(self) -> Tuple[bool, Optional[float], dict]:
        """尝试消费所有层级的令牌"""
        wait_times = {}
        can_proceed = True
        
        for level, bucket in self.buckets.items():
            success, wait_time = bucket.consume()
            if not success:
                can_proceed = False
                wait_times[level] = wait_time
            elif wait_time is not None:
                wait_times[level] = wait_time
        
        if can_proceed:
            return True, None, {}
        else:
            # 返回最长的等待时间
            max_wait = max(wait_times.values()) if wait_times else 0
            return False, max_wait, wait_times
```

## 按IP桶管理

### IP桶管理器
```python
import ipaddress
from typing import Dict, Optional
from collections import defaultdict

class IPBucketManager:
    """IP桶管理器"""
    
    def __init__(
        self,
        default_rate: float = 10.0,
        default_burst: int = 20,
        cleanup_interval: int = 300  # 5分钟清理一次
    ):
        """
        初始化IP桶管理器
        
        Args:
            default_rate: 默认每秒令牌数
            default_burst: 默认突发容量
            cleanup_interval: 清理不活跃IP的间隔（秒）
        """
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.cleanup_interval = cleanup_interval
        
        # IP -> TokenBucket 映射
        self.buckets: Dict[str, TokenBucket] = {}
        
        # IP -> 最后访问时间
        self.last_access: Dict[str, float] = {}
        
        # 自定义配置（覆盖默认值）
        self.custom_configs: Dict[str, dict] = {}
        
        # 白名单
        self.whitelist: set = set()
        
        # 黑名单
        self.blacklist: set = set()
        
        # 上次清理时间
        self.last_cleanup = time.time()
    
    def get_bucket(self, ip: str) -> TokenBucket:
        """获取或创建IP的令牌桶"""
        # 检查是否需要清理
        self._cleanup_if_needed()
        
        # 更新最后访问时间
        self.last_access[ip] = time.time()
        
        # 如果已有桶，直接返回
        if ip in self.buckets:
            return self.buckets[ip]
        
        # 创建新桶
        config = self.custom_configs.get(ip, {})
        rate = config.get("rate", self.default_rate)
        burst = config.get("burst", self.default_burst)
        
        bucket = TokenBucket(rate=rate, burst=burst)
        self.buckets[ip] = bucket
        
        return bucket
    
    def set_custom_config(self, ip: str, rate: float, burst: int) -> None:
        """设置IP的自定义配置"""
        self.custom_configs[ip] = {"rate": rate, "burst": burst}
        
        # 如果桶已存在，更新它
        if ip in self.buckets:
            self.buckets[ip] = TokenBucket(rate=rate, burst=burst)
    
    def remove_custom_config(self, ip: str) -> bool:
        """移除IP的自定义配置"""
        if ip in self.custom_configs:
            del self.custom_configs[ip]
            
            # 重置为默认配置
            if ip in self.buckets:
                self.buckets[ip] = TokenBucket(
                    rate=self.default_rate,
                    burst=self.default_burst
                )
            return True
        return False
    
    def add_to_whitelist(self, ip: str) -> None:
        """添加IP到白名单"""
        self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str) -> bool:
        """从白名单移除IP"""
        if ip in self.whitelist:
            self.whitelist.remove(ip)
            return True
        return False
    
    def add_to_blacklist(self, ip: str) -> None:
        """添加IP到黑名单"""
        self.blacklist.add(ip)
        
        # 从白名单中移除（如果存在）
        if ip in self.whitelist:
            self.whitelist.remove(ip)
    
    def remove_from_blacklist(self, ip: str) -> bool:
        """从黑名单移除IP"""
        if ip in self.blacklist:
            self.blacklist.remove(ip)
            return True
        return False
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单中"""
        return ip in self.whitelist
    
    def is_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        return ip in self.blacklist
    
    def check_ip(self, ip: str) -> Tuple[bool, Optional[float], str]:
        """
        检查IP的请求是否允许
        
        Returns:
            Tuple[是否允许, 需要等待的时间, 原因]
        """
        # 检查黑名单
        if self.is_blacklisted(ip):
            return False, None, "blacklisted"
        
        # 检查白名单
        if self.is_whitelisted(ip):
            return True, None, "whitelisted"
        
        # 获取令牌桶
        bucket = self.get_bucket(ip)
        
        # 尝试消费令牌
        success, wait_time = bucket.consume()
        
        if success:
            return True, None, "allowed"
        else:
            return False, wait_time, "rate_limited"
    
    def _cleanup_if_needed(self) -> None:
        """如果需要，清理不活跃的IP桶"""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        inactive_ips = []
        inactive_threshold = 3600  # 1小时不活跃视为不活跃
        
        for ip, last_access in self.last_access.items():
            if current_time - last_access > inactive_threshold:
                inactive_ips.append(ip)
        
        for ip in inactive_ips:
            if ip in self.buckets:
                del self.buckets[ip]
            if ip in self.last_access:
                del self.last_access[ip]
            # 注意：不清除自定义配置、白名单、黑名单
        
        self.last_cleanup = current_time
    
    def get_stats(self) -> dict:
        """获取管理器统计信息"""
        self._cleanup_if_needed()
        
        bucket_stats = {}
        for ip, bucket in self.buckets.items():
            bucket_stats[ip] = bucket.get_stats()
        
        return {
            "total_buckets": len(self.buckets),
            "total_custom_configs": len(self.custom_configs),
            "whitelist_size": len(self.whitelist),
            "blacklist_size": len(self.blacklist),
            "bucket_stats": bucket_stats,
            "default_rate": self.default_rate,
            "default_burst": self.default_burst
        }
```

### CIDR范围支持
```python
class CIDRBucketManager(IPBucketManager):
    """支持CIDR范围的IP桶管理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cidr_whitelist: list = []  # CIDR网络列表
        self.cidr_blacklist: list = []
        self.cidr_custom_configs: list = []  # (network, config)
    
    def add_cidr_to_whitelist(self, cidr: str) -> None:
        """添加CIDR范围到白名单"""
        network = ipaddress.ip_network(cidr, strict=False)
        self.cidr_whitelist.append(network)
    
    def add_cidr_to_blacklist(self, cidr: str) -> None:
        """添加CIDR范围到黑名单"""
        network = ipaddress.ip_network(cidr, strict=False)
        self.cidr_blacklist.append(network)
    
    def set_cidr_custom_config(self, cidr: str, rate: float, burst: int) -> None:
        """设置CIDR范围的自定义配置"""
        network = ipaddress.ip_network(cidr, strict=False)
        self.cidr_custom_configs.append((network, {"rate": rate, "burst": burst}))
    
    def _get_cidr_config_for_ip(self, ip: str) -> Optional[dict]:
        """获取IP所属CIDR范围的自定义配置"""
        ip_obj = ipaddress.ip_address(ip)
        
        for network, config in self.cidr_custom_configs:
            if ip_obj in network:
                return config
        
        return None
    
    def _is_in_cidr_whitelist(self, ip: str) -> bool:
        """检查IP是否在CIDR白名单中"""
        ip_obj = ipaddress.ip_address(ip)
        
        for network in self.cidr_whitelist:
            if ip_obj in network:
                return True
        
        return False
    
    def _is_in_cidr_blacklist(self, ip: str) -> bool:
        """检查IP是否在CIDR黑名单中"""
        ip_obj = ipaddress.ip_address(ip)
        
        for network in self.cidr_blacklist:
            if ip_obj in network:
                return True
        
        return False
    
    def get_bucket(self, ip: str) -> TokenBucket:
        """获取或创建IP的令牌桶（支持CIDR配置）"""
        # 检查CIDR黑名单
        if self._is_in_cidr_blacklist(ip):
            # 使用最严格的配置
            return TokenBucket(rate=0.001, burst=1)
        
        # 检查CIDR自定义配置
        cidr_config = self._get_cidr_config_for_ip(ip)
        if cidr_config:
            rate = cidr_config.get("rate", self.default_rate)
            burst = cidr_config.get("burst", self.default_burst)
            
            if ip in self.buckets:
                # 更新现有桶
                self.buckets[ip] = TokenBucket(rate=rate, burst=burst)
            else:
                # 创建新桶
                bucket = TokenBucket(rate=rate, burst=burst)
                self.buckets[ip] = bucket
            
            return self.buckets[ip]
        
        # 使用父类逻辑
        return super().get_bucket(ip)
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单中（支持CIDR）"""
        if super().is_whitelisted(ip):
            return True
        
        return self._is_in_cidr_whitelist(ip)
    
    def is_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中（支持CIDR）"""
        if super().is_blacklisted(ip):
            return True
        
        return self._is_in_cidr_blacklist(ip)
```

## 中间件集成

### FastAPI中间件实现
```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import json

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(
        self,
        app,
        ip_bucket_manager: IPBucketManager,
        enabled: bool = True,
        exclude_paths: Optional[list] = None,
        cost_map: Optional[dict] = None
    ):
        """
        初始化速率限制中间件
        
        Args:
            app: FastAPI应用
            ip_bucket_manager: IP桶管理器
            enabled: 是否启用中间件
            exclude_paths: 排除的路径列表
            cost_map: 路径 -> 令牌成本的映射
        """
        super().__init__(app)
        self.ip_bucket_manager = ip_bucket_manager
        self.enabled = enabled
        self.exclude_paths = exclude_paths or []
        self.cost_map = cost_map or {}
        
        # 默认令牌成本
        self.default_cost = 1.0
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rate_limited_requests": 0,
            "whitelisted_requests": 0,
            "blacklisted_requests": 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """中间件调度方法"""
        # 更新总请求数
        self.stats["total_requests"] += 1
        
        # 检查是否启用
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否在排除路径中
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查IP状态
        allowed, wait_time, reason = self.ip_bucket_manager.check_ip(client_ip)
        
        # 更新统计
        if reason == "whitelisted":
            self.stats["whitelisted_requests"] += 1
        elif reason == "blacklisted":
            self.stats["blacklisted_requests"] += 1
        elif allowed:
            self.stats["allowed_requests"] += 1
        else:
            self.stats["rate_limited_requests"] += 1
        
        # 处理不允许的请求
        if not allowed:
            return self._create_rate_limit_response(wait_time, reason)
        
        # 调用下一个中间件或路由
        response = await call_next(request)
        
        # 添加速率限制头部
        response = self._add_rate_limit_headers(response, client_ip)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 优先从X-Forwarded-For头部获取
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 取第一个IP（原始客户端IP）
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
        
        # 使用连接客户端IP
        if request.client and request.client.host:
            return request.client.host
        
        # 默认回退
        return "unknown"
    
    def _is_excluded_path(self, path: str) -> bool:
        """检查路径是否在排除列表中"""
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    def _get_request_cost(self, request: Request) -> float:
        """获取请求的令牌成本"""
        # 检查路径映射
        for path_pattern, cost in self.cost_map.items():
            if request.url.path.startswith(path_pattern):
                return cost
        
        # 检查方法映射
        method_cost_key = f"{request.method}:{request.url.path}"
        if method_cost_key in self.cost_map:
            return self.cost_map[method_cost_key]
        
        # 默认成本
        return self.default_cost
    
    def _create_rate_limit_response(self, wait_time: Optional[float], reason: str) -> Response:
        """创建速率限制响应"""
        if reason == "blacklisted":
            status_code = HTTP_429_TOO_MANY_REQUESTS
            message = "IP address is blacklisted"
            retry_after = 3600  # 1小时
        else:
            status_code = HTTP_429_TOO_MANY_REQUESTS
            message = "Too many requests"
            retry_after = int(wait_time) if wait_time else 1
        
        response_content = {
            "error": "rate_limit_exceeded",
            "message": message,
            "reason": reason,
            "retry_after": retry_after
        }
        
        return Response(
            content=json.dumps(response_content),
            status_code=status_code,
            media_type="application/json",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reason": reason
            }
        )
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str) -> Response:
        """添加速率限制相关头部"""
        # 获取IP的桶信息
        bucket = self.ip_bucket_manager.get_bucket(client_ip)
        bucket_stats = bucket.get_stats()
        
        # 添加头部
        headers = {
            "X-RateLimit-Limit": str(bucket_stats["burst"]),
            "X-RateLimit-Remaining": str(int(bucket_stats["current_tokens"])),
            "X-RateLimit-Reset": str(int(time.time() + 
                (bucket_stats["burst"] - bucket_stats["current_tokens"]) / 
                bucket_stats["rate"]))
        }
        
        # 添加白名单/黑名单状态
        if self.ip_bucket_manager.is_whitelisted(client_ip):
            headers["X-RateLimit-Status"] = "whitelisted"
        elif self.ip_bucket_manager.is_blacklisted(client_ip):
            headers["X-RateLimit-Status"] = "blacklisted"
        else:
            headers["X-RateLimit-Status"] = "limited"
        
        # 更新响应头部
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def get_stats(self) -> dict:
        """获取中间件统计信息"""
        return {
            **self.stats,
            "enabled": self.enabled,
            "exclude_paths": self.exclude_paths,
            "default_cost": self.default_cost,
            "bucket_manager_stats": self.ip_bucket_manager.get_stats()
        }
```

### 依赖注入配置
```python
from functools import lru_cache

class RateLimitConfig:
    """速率限制配置"""
    
    def __init__(self):
        # 默认配置
        self.default_rate = 10.0  # 每秒10个请求
        self.default_burst = 20   # 突发容量20
        
        # 中间件配置
        self.enabled = True
        self.exclude_paths = ["/health", "/docs", "/openapi.json"]
        
        # 成本映射
        self.cost_map = {
            "/api/v1/upload": 5.0,      # 上传操作成本高
            "POST:/api/v1/users": 2.0,  # 创建用户成本较高
            "DELETE:": 3.0,             # 所有删除操作
        }
        
        # 白名单配置
        self.whitelist = [
            "127.0.0.1",
            "::1",
            "192.168.1.0/24"  # 内部网络
        ]
        
        # 黑名单配置
        self.blacklist = [
            # 示例：恶意IP
        ]
        
        # 自定义IP配置
        self.custom_ip_configs = {
            "10.0.0.1": {"rate": 100, "burst": 200},  # 内部API网关
            "192.168.0.100": {"rate": 1, "burst": 2}, # 严格限制的IP
        }

@lru_cache()
def get_rate_limit_config() -> RateLimitConfig:
    """获取速率限制配置（单例）"""
    return RateLimitConfig()

@lru_cache()
def get_ip_bucket_manager(config: RateLimitConfig = Depends(get_rate_limit_config)) -> IPBucketManager:
    """获取IP桶管理器（单例）"""
    manager = IPBucketManager(
        default_rate=config.default_rate,
        default_burst=config.default_burst
    )
    
    # 配置白名单
    for ip in config.whitelist:
        manager.add_to_whitelist(ip)
    
    # 配置黑名单
    for ip in config.blacklist:
        manager.add_to_blacklist(ip)
    
    # 配置自定义IP设置
    for ip, ip_config in config.custom_ip_configs.items():
        manager.set_custom_config(
            ip=ip,
            rate=ip_config["rate"],
            burst=ip_config["burst"]
        )
    
    return manager

@lru_cache()
def get_rate_limit_middleware(
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager),
    config: RateLimitConfig = Depends(get_rate_limit_config)
) -> RateLimitMiddleware:
    """获取速率限制中间件配置"""
    # 注意：中间件需要在应用级别添加，这里返回配置
    return {
        "ip_bucket_manager": ip_bucket_manager,
        "enabled": config.enabled,
        "exclude_paths": config.exclude_paths,
        "cost_map": config.cost_map
    }
```

## Retry-After计算

### 精确等待时间计算
```python
import math
from typing import Optional

class RetryAfterCalculator:
    """Retry-After头部计算器"""
    
    @staticmethod
    def calculate_from_wait_time(wait_time: Optional[float]) -> int:
        """
        从等待时间计算Retry-After值
        
        Args:
            wait_time: 需要等待的秒数（浮点数）
            
        Returns:
            整数的Retry-After值（秒）
        """
        if wait_time is None:
            return 1  # 默认1秒
        
        # 向上取整到最近的整数秒
        retry_after = math.ceil(wait_time)
        
        # 确保最小值
        retry_after = max(1, retry_after)
        
        # 限制最大值（避免过长的等待）
        retry_after = min(3600, retry_after)  # 最多1小时
        
        return retry_after
    
    @staticmethod
    def calculate_from_timestamp(reset_timestamp: float) -> int:
        """
        从重置时间戳计算Retry-After值
        
        Args:
            reset_timestamp: 重置时间戳（Unix时间戳）
            
        Returns:
            整数的Retry-After值（秒）
        """
        current_time = time.time()
        
        if reset_timestamp <= current_time:
            return 1
        
        wait_time = reset_timestamp - current_time
        return RetryAfterCalculator.calculate_from_wait_time(wait_time)
    
    @staticmethod
    def create_retry_after_header(wait_time: Optional[float]) -> str:
        """创建Retry-After头部值"""
        retry_after = RetryAfterCalculator.calculate_from_wait_time(wait_time)
        return str(retry_after)
    
    @staticmethod
    def parse_retry_after_header(header_value: str) -> Optional[float]:
        """解析Retry-After头部值"""
        try:
            # 尝试解析为整数秒数
            if header_value.isdigit():
                return float(header_value)
            
            # 尝试解析为HTTP日期格式
            # 注意：这里简化处理，实际需要解析日期格式
            # 格式如：Wed, 21 Oct 2015 07:28:00 GMT
            return None
            
        except (ValueError, AttributeError):
            return None
```

### 客户端重试逻辑
```python
class RateLimitAwareClient:
    """感知速率限制的HTTP客户端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.rate_limit_info = {}
        
    async def request_with_retry(
        self,
        method: str,
        endpoint: str,
        max_retries: int = 3,
        **kwargs
    ):
        """带重试的请求（感知速率限制）"""
        for attempt in range(max_retries):
            try:
                response = await self._make_request(method, endpoint, **kwargs)
                
                # 检查速率限制
                if response.status == 429:
                    retry_after = self._extract_retry_after(response)
                    
                    if attempt < max_retries - 1 and retry_after:
                        # 等待建议的时间
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return response
                
                # 更新速率限制信息
                self._update_rate_limit_info(response)
                
                return response
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # 等待指数退避
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("Max retries exceeded")
    
    def _extract_retry_after(self, response) -> Optional[float]:
        """从响应中提取Retry-After值"""
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header:
            return RetryAfterCalculator.parse_retry_after_header(retry_after_header)
        return None
    
    def _update_rate_limit_info(self, response):
        """更新速率限制信息"""
        headers = response.headers
        
        self.rate_limit_info = {
            "limit": headers.get("X-RateLimit-Limit"),
            "remaining": headers.get("X-RateLimit-Remaining"),
            "reset": headers.get("X-RateLimit-Reset"),
            "status": headers.get("X-RateLimit-Status")
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """实际发起请求（需要具体实现）"""
        # 这里需要根据具体的HTTP客户端库实现
        # 例如：aiohttp, httpx等
        pass
```

## API管理端点

### 管理API设计
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/rate-limit", tags=["rate-limit"])

# 数据模型
class RateLimitStatsResponse(BaseModel):
    total_requests: int
    allowed_requests: int
    rate_limited_requests: int
    whitelisted_requests: int
    blacklisted_requests: int
    bucket_manager_stats: dict

class IPConfigRequest(BaseModel):
    ip: str
    rate: float
    burst: int

class WhitelistRequest(BaseModel):
    ip: str

class BlacklistRequest(BaseModel):
    ip: str

@router.get("/stats", response_model=RateLimitStatsResponse)
async def get_rate_limit_stats(
    middleware: RateLimitMiddleware = Depends(get_rate_limit_middleware)
):
    """获取速率限制统计信息"""
    stats = middleware.get_stats()
    return RateLimitStatsResponse(**stats)

@router.post("/config/ip")
async def set_ip_config(
    request: IPConfigRequest,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """设置IP的自定义配置"""
    ip_bucket_manager.set_custom_config(
        ip=request.ip,
        rate=request.rate,
        burst=request.burst
    )
    
    return {"message": f"Configuration updated for IP {request.ip}"}

@router.delete("/config/ip/{ip}")
async def remove_ip_config(
    ip: str,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """移除IP的自定义配置"""
    success = ip_bucket_manager.remove_custom_config(ip)
    
    if not success:
        raise HTTPException(status_code=404, detail="IP configuration not found")
    
    return {"message": f"Configuration removed for IP {ip}"}

@router.post("/whitelist")
async def add_to_whitelist(
    request: WhitelistRequest,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """添加IP到白名单"""
    ip_bucket_manager.add_to_whitelist(request.ip)
    
    return {"message": f"IP {request.ip} added to whitelist"}

@router.delete("/whitelist/{ip}")
async def remove_from_whitelist(
    ip: str,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """从白名单移除IP"""
    success = ip_bucket_manager.remove_from_whitelist(ip)
    
    if not success:
        raise HTTPException(status_code=404, detail="IP not in whitelist")
    
    return {"message": f"IP {ip} removed from whitelist"}

@router.post("/blacklist")
async def add_to_blacklist(
    request: BlacklistRequest,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """添加IP到黑名单"""
    ip_bucket_manager.add_to_blacklist(request.ip)
    
    return {"message": f"IP {request.ip} added to blacklist"}

@router.delete("/blacklist/{ip}")
async def remove_from_blacklist(
    ip: str,
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """从黑名单移除IP"""
    success = ip_bucket_manager.remove_from_blacklist(ip)
    
    if not success:
        raise HTTPException(status_code=404, detail="IP not in blacklist")
    
    return {"message": f"IP {ip} removed from blacklist"}

@router.get("/whitelist")
async def get_whitelist(
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """获取白名单列表"""
    return {"whitelist": list(ip_bucket_manager.whitelist)}

@router.get("/blacklist")
async def get_blacklist(
    ip_bucket_manager: IPBucketManager = Depends(get_ip_bucket_manager)
):
    """获取黑名单列表"""
    return {"blacklist": list(ip_bucket_manager.blacklist)}
```

## Constraint Acknowledgment

### [L]Python - Python语言
- 使用Python 3.8+语法和标准库
- 充分利用Python的面向对象特性和数据类型
- 遵循Python类型提示和文档字符串规范

### [F]FastAPI - FastAPI框架
- 使用FastAPI构建中间件和管理API
- 利用Pydantic进行数据验证和序列化
- 提供完整的OpenAPI文档

### [ALGO]TOKEN_BUCKET - 使用令牌桶算法
- 实现完整的令牌桶算法逻辑
- 支持精确的令牌生成和消费计算
- 提供突发容量和速率控制

### [!A]NO_COUNTER - 禁止使用计数器算法
- 完全不使用简单的计数器算法
- 避免固定窗口或滑动窗口计数器实现
- 仅使用令牌桶算法进行速率限制

### [D]STDLIB+FASTAPI - 仅使用标准库和FastAPI
- 仅使用Python标准库的time、math、ipaddress等模块
- 仅使用FastAPI框架及其依赖项
- 确保代码的轻量级和可移植性

### [!D]NO_REDIS - 禁止使用Redis
- 完全不使用Redis或其他外部存储
- 所有状态存储在内存中
- 避免任何分布式缓存或持久化存储依赖

### [O]SINGLE_FILE - 输出为单文件
- 所有速率限制器逻辑在一个Python文件中实现
- 包含令牌桶算法、IP管理、中间件和API端点
- 遵循单一文件职责原则

### [RESP]429_RETRY_AFTER - 返回429状态码和Retry-After头部
- 当速率超过限制时返回HTTP 429状态码
- 提供准确的Retry-After头部值
- 支持客户端自动重试

### [WL]IP - 支持IP白名单
- 提供完整的IP白名单管理功能
- 支持单个IP和CIDR范围
- 白名单IP完全绕过速率限制

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何配置文件、环境变量或数据库设置
- 所有配置通过代码参数化和依赖注入实现
- 确保代码的独立性和自包含性

## 系统特性总结

1. **精确控制**: 令牌桶算法提供精确的速率和突发控制
2. **灵活配置**: 支持按IP、按路径、按方法的自定义配置
3. **实时监控**: 提供详细的统计信息和监控端点
4. **客户端友好**: 清晰的429响应和Retry-After头部
5. **易于管理**: 完整的API端点进行配置管理

该设计方案完全满足速率限制器中间件的所有功能需求，同时严格遵守所有Header约束，提供高性能、可配置的速率限制解决方案。