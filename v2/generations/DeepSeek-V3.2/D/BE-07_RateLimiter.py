import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 令牌桶算法实现
class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        """
        初始化令牌桶
        
        Args:
            rate: 每秒添加的令牌数
            capacity: 桶的最大容量
        """
        self.rate = rate  # 令牌/秒
        self.capacity = capacity  # 最大令牌数
        self.tokens = capacity  # 当前令牌数
        self.last_refill = time.time()  # 上次补充时间
        self.lock = threading.Lock()  # 线程锁
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        time_passed = now - self.last_refill
        
        # 计算应补充的令牌数
        new_tokens = time_passed * self.rate
        
        if new_tokens > 0:
            with self.lock:
                # 更新令牌数，不超过容量
                self.tokens = min(self.capacity, self.tokens + new_tokens)
                self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        消费令牌
        
        Args:
            tokens: 要消费的令牌数
        
        Returns:
            bool: 是否成功消费
        """
        self._refill()
        
        with self.lock:
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_tokens(self) -> float:
        """获取当前令牌数"""
        self._refill()
        return self.tokens
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        获取需要等待的时间（秒）
        
        Args:
            tokens: 需要消费的令牌数
        
        Returns:
            float: 需要等待的时间（秒）
        """
        self._refill()
        
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            
            # 计算需要等待的时间
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate

# 限流器管理器
class RateLimiter:
    def __init__(self, default_rate: float = 10.0, default_capacity: int = 20):
        """
        初始化限流器管理器
        
        Args:
            default_rate: 默认速率（令牌/秒）
            default_capacity: 默认容量
        """
        self.default_rate = default_rate
        self.default_capacity = default_capacity
        self.buckets: Dict[str, TokenBucket] = {}
        self.whitelist: Set[str] = set()
        self.lock = threading.Lock()
    
    def get_bucket(self, key: str) -> TokenBucket:
        """获取或创建令牌桶"""
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(self.default_rate, self.default_capacity)
            return self.buckets[key]
    
    def set_rate(self, key: str, rate: float, capacity: int = None):
        """设置特定key的速率和容量"""
        with self.lock:
            if key in self.buckets:
                # 更新现有桶
                bucket = self.buckets[key]
                bucket.rate = rate
                if capacity is not None:
                    bucket.capacity = capacity
            else:
                # 创建新桶
                cap = capacity if capacity is not None else self.default_capacity
                self.buckets[key] = TokenBucket(rate, cap)
    
    def add_to_whitelist(self, ip: str):
        """添加IP到白名单"""
        with self.lock:
            self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        """从白名单移除IP"""
        with self.lock:
            self.whitelist.discard(ip)
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单中"""
        return ip in self.whitelist
    
    def consume(self, key: str, tokens: int = 1) -> Tuple[bool, float]:
        """
        尝试消费令牌
        
        Args:
            key: 标识符（如IP地址）
            tokens: 要消费的令牌数
        
        Returns:
            Tuple[bool, float]: (是否成功, 需要等待的时间)
        """
        bucket = self.get_bucket(key)
        
        if bucket.consume(tokens):
            return True, 0.0
        
        wait_time = bucket.get_wait_time(tokens)
        return False, wait_time
    
    def get_status(self, key: str) -> Dict:
        """获取key的当前状态"""
        bucket = self.get_bucket(key)
        
        return {
            "key": key,
            "current_tokens": bucket.get_tokens(),
            "rate": bucket.rate,
            "capacity": bucket.capacity,
            "whitelisted": self.is_whitelisted(key)
        }
    
    def get_all_status(self) -> List[Dict]:
        """获取所有key的状态"""
        with self.lock:
            return [self.get_status(key) for key in self.buckets.keys()]

# FastAPI应用
app = FastAPI(
    title="令牌桶限流服务",
    description="基于令牌桶算法的API限流服务",
    version="1.0.0"
)

# 全局限流器实例
rate_limiter = RateLimiter(default_rate=5.0, default_capacity=10)

# 请求模型
class RateLimitConfig(BaseModel):
    rate: float = 10.0  # 令牌/秒
    capacity: int = 20  # 最大令牌数

class WhitelistRequest(BaseModel):
    ip: str

# 获取客户端IP
def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 尝试从X-Forwarded-For获取真实IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个IP
        return forwarded.split(",")[0].strip()
    
    # 回退到客户端地址
    return request.client.host if request.client else "127.0.0.1"

# 限流中间件
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """限流中间件"""
    # 获取客户端IP
    client_ip = get_client_ip(request)
    
    # 检查白名单
    if rate_limiter.is_whitelisted(client_ip):
        response = await call_next(request)
        response.headers["X-RateLimit-Whitelisted"] = "true"
        return response
    
    # 获取请求路径
    path = request.url.path
    
    # 不同路径消耗不同令牌数
    tokens_needed = 1
    
    if request.method == "POST":
        tokens_needed = 2
    elif request.method == "DELETE":
        tokens_needed = 3
    
    # 尝试消费令牌
    allowed, wait_time = rate_limiter.consume(client_ip, tokens_needed)
    
    if not allowed:
        # 计算重试时间
        retry_after = int(wait_time) + 1
        
        # 返回429 Too Many Requests
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": f"请求过于频繁，请稍后再试",
                "retry_after": retry_after,
                "wait_time_seconds": wait_time
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(rate_limiter.default_rate),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + wait_time))
            }
        )
    
    # 获取剩余令牌数
    bucket = rate_limiter.get_bucket(client_ip)
    remaining_tokens = bucket.get_tokens()
    
    # 处理请求
    response = await call_next(request)
    
    # 添加限流头信息
    response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
    response.headers["X-RateLimit-Remaining"] = str(int(remaining_tokens))
    response.headers["X-RateLimit-Reset"] = str(int(bucket.last_refill + 1))
    
    return response

# API端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "令牌桶限流服务",
        "endpoints": {
            "GET /": "此文档",
            "GET /api/test": "测试端点（受限流保护）",
            "POST /api/test": "测试端点（消耗更多令牌）",
            "GET /status": "查看请求者状态",
            "GET /status/all": "查看所有请求者状态",
            "POST /config": "配置限流参数",
            "POST /whitelist/add": "添加IP到白名单",
            "POST /whitelist/remove": "从白名单移除IP",
            "GET /whitelist": "查看白名单"
        },
        "default_rate": rate_limiter.default_rate,
        "default_capacity": rate_limiter.default_capacity
    }

@app.get("/api/test")
async def test_endpoint(request: Request):
    """测试端点（受限流保护）"""
    client_ip = get_client_ip(request)
    
    return {
        "message": "测试成功！",
        "client_ip": client_ip,
        "timestamp": datetime.now().isoformat(),
        "whitelisted": rate_limiter.is_whitelisted(client_ip),
        "method": request.method
    }

@app.post("/api/test")
async def test_post_endpoint(request: Request):
    """测试POST端点（消耗更多令牌）"""
    client_ip = get_client_ip(request)
    
    return {
        "message": "POST测试成功！",
        "client_ip": client_ip,
        "timestamp": datetime.now().isoformat(),
        "whitelisted": rate_limiter.is_whitelisted(client_ip),
        "method": request.method,
        "warning": "POST请求消耗2个令牌"
    }

@app.get("/status")
async def get_status(request: Request):
    """获取当前请求者的状态"""
    client_ip = get_client_ip(request)
    status_info = rate_limiter.get_status(client_ip)
    
    return {
        "status": "success",
        "client_ip": client_ip,
        **status_info
    }

@app.get("/status/all")
async def get_all_status():
    """获取所有请求者的状态"""
    all_status = rate_limiter.get_all_status()
    
    return {
        "status": "success",
        "count": len(all_status),
        "clients": all_status
    }

@app.post("/config")
async def configure_rate_limit(config: RateLimitConfig, request: Request):
    """配置限流参数"""
    client_ip = get_client_ip(request)
    
    rate_limiter.set_rate(
        client_ip,
        config.rate,
        config.capacity
    )
    
    return {
        "status": "success",
        "message": "限流配置已更新",
        "client_ip": client_ip,
        "new_rate": config.rate,
        "new_capacity": config.capacity
    }

@app.post("/whitelist/add")
async def add_to_whitelist(whitelist_req: WhitelistRequest, request: Request):
    """添加IP到白名单"""
    admin_ip = get_client_ip(request)
    
    # 简单的管理员检查（生产环境应使用更安全的认证）
    if admin_ip != "127.0.0.1":
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以修改白名单"
        )
    
    rate_limiter.add_to_whitelist(whitelist_req.ip)
    
    return {
        "status": "success",
        "message": f"IP {whitelist_req.ip} 已添加到白名单",
        "whitelist_count": len(rate_limiter.whitelist)
    }

@app.post("/whitelist/remove")
async def remove_from_whitelist(whitelist_req: WhitelistRequest, request: Request):
    """从白名单移除IP"""
    admin_ip = get_client_ip(request)
    
    # 简单的管理员检查
    if admin_ip != "127.0.0.1":
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以修改白名单"
        )
    
    rate_limiter.remove_from_whitelist(whitelist_req.ip)
    
    return {
        "status": "success",
        "message": f"IP {whitelist_req.ip} 已从白名单移除",
        "whitelist_count": len(rate_limiter.whitelist)
    }

@app.get("/whitelist")
async def get_whitelist(request: Request):
    """获取白名单列表"""
    admin_ip = get_client_ip(request)
    
    # 简单的管理员检查
    if admin_ip != "127.0.0.1":
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以查看白名单"
        )
    
    return {
        "status": "success",
        "whitelist": list(rate_limiter.whitelist),
        "count": len(rate_limiter.whitelist)
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bucket_count": len(rate_limiter.buckets),
        "whitelist_count": len(rate_limiter.whitelist)
    }

# 监控端点
@app.get("/metrics")
async def get_metrics():
    """获取监控指标"""
    all_status = rate_limiter.get_all_status()
    
    total_tokens = sum(status["current_tokens"] for status in all_status)
    avg_tokens = total_tokens / len(all_status) if all_status else 0
    
    return {
        "total_clients": len(all_status),
        "total_tokens": total_tokens,
        "average_tokens": avg_tokens,
        "whitelisted_ips": len(rate_limiter.whitelist),
        "timestamp": time.time()
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("令牌桶限流服务已启动")
    
    # 添加一些默认白名单IP
    rate_limiter.add_to_whitelist("127.0.0.1")
    
    print(f"默认速率: {rate_limiter.default_rate} 令牌/秒")
    print(f"默认容量: {rate_limiter.default_capacity} 令牌")
    print(f"白名单IP数: {len(rate_limiter.whitelist)}")

if __name__ == "__main__":
    uvicorn.run(
        "BE_07_RateLimiter:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )