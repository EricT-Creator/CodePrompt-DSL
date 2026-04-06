#!/usr/bin/env python3
"""
速率限制器 - 使用FastAPI实现令牌桶算法
支持每IP限制、白名单和统计信息
"""

import time
import ipaddress
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator


# 数据模型
class RateLimitConfig(BaseModel):
    """速率限制配置"""
    requests_per_second: float = Field(1.0, ge=0.1, le=1000, description="每秒请求数")
    burst_size: int = Field(10, ge=1, le=10000, description="突发请求容量")
    enabled: bool = Field(True, description="是否启用速率限制")
    
    @validator('requests_per_second')
    def validate_rate(cls, v):
        if v <= 0:
            raise ValueError('请求速率必须大于0')
        return v


class RateLimitStatus(BaseModel):
    """速率限制状态"""
    ip_address: str
    tokens: float
    last_refill: float
    requests_count: int = 0
    limited_requests: int = 0
    first_seen: float
    last_seen: float
    is_whitelisted: bool = False


class ClientStats(BaseModel):
    """客户端统计信息"""
    ip_address: str
    total_requests: int = 0
    successful_requests: int = 0
    limited_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: float = 0.0
    first_request_time: float = 0.0


class RateLimitResponse(BaseModel):
    """速率限制响应"""
    limited: bool
    remaining_tokens: float
    reset_after: float  # 重置所需秒数
    retry_after: Optional[float] = None  # 重试等待秒数（如果被限制）
    limit_info: Dict[str, Any]


# 令牌桶实现
class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, rate: float, burst: int):
        """
        初始化令牌桶
        
        Args:
            rate: 每秒添加的令牌数
            burst: 最大令牌容量
        """
        self.rate = rate  # 令牌/秒
        self.capacity = burst  # 最大容量
        self.tokens = burst  # 当前令牌数
        self.last_refill = time.time()
    
    def refill(self) -> None:
        """补充令牌"""
        now = time.time()
        time_passed = now - self.last_refill
        
        if time_passed > 0:
            new_tokens = time_passed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> bool:
        """
        尝试消费令牌
        
        Args:
            tokens: 需要消费的令牌数
            
        Returns:
            bool: 是否成功消费
        """
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_remaining(self) -> float:
        """获取剩余令牌数"""
        self.refill()
        return self.tokens
    
    def get_time_to_next_token(self) -> float:
        """获取下一个令牌的时间（秒）"""
        if self.tokens < self.capacity:
            return 1.0 / self.rate
        return 0.0
    
    def get_reset_time(self) -> float:
        """获取完全重置所需时间（秒）"""
        if self.tokens < self.capacity:
            return (self.capacity - self.tokens) / self.rate
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "rate": self.rate,
            "capacity": self.capacity,
            "tokens": self.get_remaining(),
            "last_refill": self.last_refill,
            "time_to_next_token": self.get_time_to_next_token(),
            "reset_time": self.get_reset_time()
        }


# IP白名单管理器
class IPWhitelist:
    """IP白名单管理器"""
    
    def __init__(self):
        self.whitelist: Set[str] = set()
        self.cidr_ranges: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    
    def add_ip(self, ip: str) -> None:
        """添加单个IP到白名单"""
        try:
            # 验证IP地址
            ip_obj = ipaddress.ip_address(ip)
            self.whitelist.add(str(ip_obj))
        except ValueError:
            raise ValueError(f"无效的IP地址: {ip}")
    
    def add_cidr(self, cidr: str) -> None:
        """添加CIDR范围到白名单"""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            self.cidr_ranges.append(network)
        except ValueError:
            raise ValueError(f"无效的CIDR范围: {cidr}")
    
    def remove_ip(self, ip: str) -> bool:
        """从白名单移除IP"""
        if ip in self.whitelist:
            self.whitelist.remove(ip)
            return True
        return False
    
    def remove_cidr(self, cidr: str) -> bool:
        """从白名单移除CIDR范围"""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            if network in self.cidr_ranges:
                self.cidr_ranges.remove(network)
                return True
        except ValueError:
            pass
        return False
    
    def is_whitelisted(self, ip: str) -> bool:
        """检查IP是否在白名单中"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # 检查精确IP匹配
            if str(ip_obj) in self.whitelist:
                return True
            
            # 检查CIDR范围匹配
            for network in self.cidr_ranges:
                if ip_obj in network:
                    return True
            
            return False
        except ValueError:
            return False
    
    def get_whitelist(self) -> Dict[str, List[str]]:
        """获取白名单信息"""
        return {
            "individual_ips": sorted(list(self.whitelist)),
            "cidr_ranges": [str(net) for net in self.cidr_ranges],
            "total_count": len(self.whitelist) + len(self.cidr_ranges)
        }


# 速率限制管理器
class RateLimitManager:
    """速率限制管理器"""
    
    def __init__(self, default_rate: float = 1.0, default_burst: int = 10):
        self.default_rate = default_rate
        self.default_burst = default_burst
        
        # IP到令牌桶的映射
        self.buckets: Dict[str, TokenBucket] = {}
        
        # IP统计信息
        self.stats: Dict[str, ClientStats] = {}
        
        # IP白名单
        self.whitelist = IPWhitelist()
        
        # 全局统计
        self.global_stats = {
            "total_requests": 0,
            "limited_requests": 0,
            "whitelisted_requests": 0,
            "start_time": time.time()
        }
        
        # IP特定配置
        self.ip_configs: Dict[str, RateLimitConfig] = {}
        
        # 清理过期IP的阈值（秒）
        self.cleanup_threshold = 3600  # 1小时
        
        # 初始化一些白名单IP（示例）
        self._init_default_whitelist()
    
    def _init_default_whitelist(self) -> None:
        """初始化默认白名单（示例）"""
        # 本地IP
        self.whitelist.add_ip("127.0.0.1")
        self.whitelist.add_ip("::1")
        
        # 示例内部网络
        self.whitelist.add_cidr("192.168.0.0/16")
        self.whitelist.add_cidr("10.0.0.0/8")
        self.whitelist.add_cidr("172.16.0.0/12")
    
    def get_or_create_bucket(self, ip: str) -> TokenBucket:
        """获取或创建令牌桶"""
        if ip not in self.buckets:
            # 获取IP特定配置或使用默认配置
            config = self.ip_configs.get(ip, None)
            if config:
                rate = config.requests_per_second
                burst = config.burst_size
            else:
                rate = self.default_rate
                burst = self.default_burst
            
            self.buckets[ip] = TokenBucket(rate, burst)
            
            # 初始化统计
            if ip not in self.stats:
                now = time.time()
                self.stats[ip] = ClientStats(
                    ip_address=ip,
                    first_request_time=now,
                    last_request_time=now
                )
        
        return self.buckets[ip]
    
    def check_rate_limit(self, ip: str, tokens: float = 1.0) -> RateLimitResponse:
        """检查速率限制"""
        # 更新全局统计
        self.global_stats["total_requests"] += 1
        
        # 检查白名单
        is_whitelisted = self.whitelist.is_whitelisted(ip)
        if is_whitelisted:
            self.global_stats["whitelisted_requests"] += 1
            
            # 更新IP统计
            if ip in self.stats:
                stats = self.stats[ip]
                stats.total_requests += 1
                stats.successful_requests += 1
                stats.last_request_time = time.time()
            
            return RateLimitResponse(
                limited=False,
                remaining_tokens=float('inf'),
                reset_after=0.0,
                retry_after=None,
                limit_info={
                    "whitelisted": True,
                    "rate": float('inf'),
                    "burst": float('inf')
                }
            )
        
        # 获取或创建令牌桶
        bucket = self.get_or_create_bucket(ip)
        
        # 尝试消费令牌
        success = bucket.consume(tokens)
        
        # 更新统计
        if ip in self.stats:
            stats = self.stats[ip]
            stats.total_requests += 1
            stats.last_request_time = time.time()
            
            if success:
                stats.successful_requests += 1
            else:
                stats.limited_requests += 1
                self.global_stats["limited_requests"] += 1
        
        # 构建响应
        remaining = bucket.get_remaining()
        reset_after = bucket.get_reset_time()
        
        limit_info = {
            "whitelisted": False,
            "rate": bucket.rate,
            "burst": bucket.capacity,
            "ip": ip,
            "bucket_status": bucket.get_status()
        }
        
        if success:
            return RateLimitResponse(
                limited=False,
                remaining_tokens=remaining,
                reset_after=reset_after,
                retry_after=None,
                limit_info=limit_info
            )
        else:
            retry_after = 1.0 / bucket.rate if bucket.rate > 0 else 1.0
            
            return RateLimitResponse(
                limited=True,
                remaining_tokens=remaining,
                reset_after=reset_after,
                retry_after=retry_after,
                limit_info=limit_info
            )
    
    def get_ip_status(self, ip: str) -> Optional[RateLimitStatus]:
        """获取IP的状态信息"""
        if ip not in self.buckets:
            return None
        
        bucket = self.buckets[ip]
        stats = self.stats.get(ip, None)
        
        return RateLimitStatus(
            ip_address=ip,
            tokens=bucket.get_remaining(),
            last_refill=bucket.last_refill,
            requests_count=stats.total_requests if stats else 0,
            limited_requests=stats.limited_requests if stats else 0,
            first_seen=stats.first_request_time if stats else time.time(),
            last_seen=stats.last_request_time if stats else time.time(),
            is_whitelisted=self.whitelist.is_whitelisted(ip)
        )
    
    def get_all_status(self, limit: int = 100) -> List[RateLimitStatus]:
        """获取所有IP的状态信息"""
        statuses = []
        for ip in list(self.buckets.keys())[:limit]:
            status = self.get_ip_status(ip)
            if status:
                statuses.append(status)
        
        return statuses
    
    def set_ip_config(self, ip: str, config: RateLimitConfig) -> None:
        """设置IP特定配置"""
        self.ip_configs[ip] = config
        
        # 如果IP已有桶，更新它
        if ip in self.buckets:
            # 创建新桶
            self.buckets[ip] = TokenBucket(
                config.requests_per_second,
                config.burst_size
            )
    
    def remove_ip_config(self, ip: str) -> bool:
        """移除IP特定配置"""
        if ip in self.ip_configs:
            del self.ip_configs[ip]
            
            # 重置为默认配置
            if ip in self.buckets:
                self.buckets[ip] = TokenBucket(
                    self.default_rate,
                    self.default_burst
                )
            return True
        return False
    
    def cleanup_inactive_ips(self, inactive_seconds: int = 3600) -> int:
        """清理不活跃的IP"""
        now = time.time()
        ips_to_remove = []
        
        for ip, bucket in self.buckets.items():
            # 检查是否在白名单中（白名单IP不清理）
            if self.whitelist.is_whitelisted(ip):
                continue
            
            # 检查是否活跃
            last_active = bucket.last_refill
            if now - last_active > inactive_seconds:
                ips_to_remove.append(ip)
        
        # 移除不活跃IP
        for ip in ips_to_remove:
            del self.buckets[ip]
            if ip in self.ip_configs:
                del self.ip_configs[ip]
        
        return len(ips_to_remove)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        uptime = time.time() - self.global_stats["start_time"]
        
        return {
            "total_requests": self.global_stats["total_requests"],
            "limited_requests": self.global_stats["limited_requests"],
            "whitelisted_requests": self.global_stats["whitelisted_requests"],
            "active_ips": len(self.buckets),
            "whitelisted_ips": len(self.whitelist.whitelist) + len(self.whitelist.cidr_ranges),
            "custom_configs": len(self.ip_configs),
            "uptime_seconds": uptime,
            "requests_per_second": self.global_stats["total_requests"] / uptime if uptime > 0 else 0,
            "start_time": self.global_stats["start_time"],
            "current_time": time.time()
        }
    
    def reset_all(self) -> None:
        """重置所有统计和桶"""
        self.buckets.clear()
        self.stats.clear()
        self.ip_configs.clear()
        self.global_stats = {
            "total_requests": 0,
            "limited_requests": 0,
            "whitelisted_requests": 0,
            "start_time": time.time()
        }


# 创建应用
app = FastAPI(
    title="速率限制器API",
    description="基于令牌桶算法的速率限制服务",
    version="1.0.0"
)

# 全局速率限制管理器
rate_limit_manager = RateLimitManager(default_rate=5.0, default_burst=20)


# 依赖：获取客户端IP
def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 尝试从X-Forwarded-For头部获取
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个IP
        ip = forwarded.split(",")[0].strip()
    else:
        # 使用客户端地址
        ip = request.client.host if request.client else "127.0.0.1"
    
    return ip


# 依赖：速率限制检查
async def rate_limit_check(
    request: Request,
    tokens: float = 1.0,
    ip: str = Depends(get_client_ip)
):
    """速率限制检查依赖"""
    # 检查速率限制
    result = rate_limit_manager.check_rate_limit(ip, tokens)
    
    # 如果被限制，返回429错误
    if result.limited:
        headers = {
            "X-RateLimit-Limit": str(result.limit_info["rate"]),
            "X-RateLimit-Remaining": str(result.remaining_tokens),
            "X-RateLimit-Reset": str(result.reset_after),
            "Retry-After": str(result.retry_after)
        }
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "请求过于频繁",
                "retry_after": result.retry_after,
                "remaining_tokens": result.remaining_tokens,
                "reset_after": result.reset_after
            },
            headers=headers
        )
    
    # 添加速率限制头部到响应
    request.state.rate_limit_result = result
    
    return result


# 中间件：添加速率限制头部
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """添加速率限制头部到响应"""
    response = await call_next(request)
    
    # 如果请求有速率限制结果，添加头部
    if hasattr(request.state, 'rate_limit_result'):
        result = request.state.rate_limit_result
        
        response.headers["X-RateLimit-Limit"] = str(result.limit_info.get("rate", 0))
        response.headers["X-RateLimit-Remaining"] = str(result.remaining_tokens)
        response.headers["X-RateLimit-Reset"] = str(result.reset_after)
        
        if result.limit_info.get("whitelisted", False):
            response.headers["X-RateLimit-Whitelisted"] = "true"
    
    return response


# API路由
@app.get("/")
async def root():
    """根路由，返回API信息"""
    return {
        "name": "速率限制器API",
        "version": "1.0.0",
        "description": "基于令牌桶算法的速率限制服务",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "API信息"},
            {"path": "/status", "method": "GET", "description": "获取当前IP的状态"},
            {"path": "/api/echo", "method": "GET", "description": "测试接口（受速率限制）"},
            {"path": "/api/delayed", "method": "GET", "description": "延迟响应测试接口"},
            {"path": "/admin/status/all", "method": "GET", "description": "获取所有IP状态（管理员）"},
            {"path": "/admin/stats", "method": "GET", "description": "获取全局统计（管理员）"},
            {"path": "/admin/whitelist", "method": "GET", "description": "获取白名单（管理员）"},
            {"path": "/admin/cleanup", "method": "POST", "description": "清理不活跃IP（管理员）"},
            {"path": "/admin/reset", "method": "POST", "description": "重置所有统计（管理员）"}
        ],
        "default_config": {
            "rate_per_second": 5.0,
            "burst_size": 20
        }
    }


@app.get("/status")
async def get_status(
    rate_limit: RateLimitResponse = Depends(rate_limit_check)
):
    """获取当前IP的状态信息"""
    ip = rate_limit.limit_info.get("ip", "unknown")
    status = rate_limit_manager.get_ip_status(ip)
    
    return {
        "ip_address": ip,
        "rate_limit_status": rate_limit.dict(),
        "detailed_status": status.dict() if status else None,
        "timestamp": time.time()
    }


@app.get("/api/echo")
async def echo_endpoint(
    message: str = "Hello, World!",
    rate_limit: RateLimitResponse = Depends(rate_limit_check)
):
    """测试接口，返回输入的消息"""
    return {
        "message": message,
        "echo": True,
        "timestamp": time.time(),
        "rate_limit_info": rate_limit.dict()
    }


@app.get("/api/delayed")
async def delayed_endpoint(
    delay: float = 1.0,
    rate_limit: RateLimitResponse = Depends(rate_limit_check)
):
    """延迟响应测试接口"""
    if delay > 10:
        raise HTTPException(status_code=400, detail="延迟时间不能超过10秒")
    
    await asyncio.sleep(delay)
    
    return {
        "message": f"延迟 {delay} 秒后响应",
        "delay_seconds": delay,
        "timestamp": time.time(),
        "rate_limit_info": rate_limit.dict()
    }


# 管理接口
@app.get("/admin/status/all")
async def get_all_status(
    limit: int = 100,
    active_only: bool = True
):
    """获取所有IP的状态信息（管理员）"""
    # 在实际应用中，这里应该添加身份验证
    
    if active_only:
        statuses = rate_limit_manager.get_all_status(limit)
    else:
        # 包括不活跃的IP（需要额外逻辑）
        statuses = rate_limit_manager.get_all_status(limit)
    
    return {
        "statuses": [status.dict() for status in statuses],
        "count": len(statuses),
        "limit": limit,
        "active_only": active_only,
        "timestamp": time.time()
    }


@app.get("/admin/stats")
async def get_admin_stats():
    """获取全局统计信息（管理员）"""
    stats = rate_limit_manager.get_global_stats()
    
    # 添加清理信息
    cleanup_threshold = rate_limit_manager.cleanup_threshold
    inactive_count = rate_limit_manager.cleanup_inactive_ips(cleanup_threshold)
    
    stats["last_cleanup"] = {
        "threshold_seconds": cleanup_threshold,
        "inactive_ips_removed": inactive_count,
        "timestamp": time.time()
    }
    
    return stats


@app.get("/admin/whitelist")
async def get_whitelist():
    """获取白名单信息（管理员）"""
    whitelist_info = rate_limit_manager.whitelist.get_whitelist()
    
    return {
        "whitelist": whitelist_info,
        "timestamp": time.time()
    }


@app.post("/admin/whitelist/add")
async def add_to_whitelist(
    ip: Optional[str] = None,
    cidr: Optional[str] = None
):
    """添加IP或CIDR到白名单（管理员）"""
    if not ip and not cidr:
        raise HTTPException(status_code=400, detail="必须提供IP或CIDR")
    
    try:
        if ip:
            rate_limit_manager.whitelist.add_ip(ip)
            message = f"IP {ip} 已添加到白名单"
        else:
            rate_limit_manager.whitelist.add_cidr(cidr)
            message = f"CIDR {cidr} 已添加到白名单"
        
        return {
            "success": True,
            "message": message,
            "timestamp": time.time()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/admin/whitelist/remove")
async def remove_from_whitelist(
    ip: Optional[str] = None,
    cidr: Optional[str] = None
):
    """从白名单移除IP或CIDR（管理员）"""
    if not ip and not cidr:
        raise HTTPException(status_code=400, detail="必须提供IP或CIDR")
    
    success = False
    if ip:
        success = rate_limit_manager.whitelist.remove_ip(ip)
        message = f"IP {ip} 已从白名单移除" if success else f"IP {ip} 不在白名单中"
    else:
        success = rate_limit_manager.whitelist.remove_cidr(cidr)
        message = f"CIDR {cidr} 已从白名单移除" if success else f"CIDR {cidr} 不在白名单中"
    
    return {
        "success": success,
        "message": message,
        "timestamp": time.time()
    }


@app.post("/admin/cleanup")
async def cleanup_inactive():
    """清理不活跃IP（管理员）"""
    removed = rate_limit_manager.cleanup_inactive_ips()
    
    return {
        "success": True,
        "message": f"清理了 {removed} 个不活跃IP",
        "removed_count": removed,
        "timestamp": time.time()
    }


@app.post("/admin/reset")
async def reset_all():
    """重置所有统计和桶（管理员）"""
    rate_limit_manager.reset_all()
    
    return {
        "success": True,
        "message": "所有统计和桶已重置",
        "timestamp": time.time()
    }


@app.post("/admin/config/ip")
async def set_ip_config(
    ip: str,
    config: RateLimitConfig
):
    """设置IP特定配置（管理员）"""
    try:
        rate_limit_manager.set_ip_config(ip, config)
        
        return {
            "success": True,
            "message": f"IP {ip} 的配置已更新",
            "config": config.dict(),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/admin/config/ip/{ip}")
async def remove_ip_config(ip: str):
    """移除IP特定配置（管理员）"""
    success = rate_limit_manager.remove_ip_config(ip)
    
    if success:
        return {
            "success": True,
            "message": f"IP {ip} 的配置已移除",
            "timestamp": time.time()
        }
    else:
        raise HTTPException(status_code=404, detail=f"IP {ip} 没有自定义配置")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "rate_limiter",
        "timestamp": time.time(),
        "uptime": time.time() - rate_limit_manager.global_stats["start_time"]
    }


# 运行应用
if __name__ == "__main__":
    import uvicorn
    
    print("启动速率限制器服务...")
    print(f"访问地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print("\n默认配置:")
    print(f"- 速率限制: {rate_limit_manager.default_rate} 请求/秒")
    print(f"- 突发容量: {rate_limit_manager.default_burst} 请求")
    print("\n白名单IP:")
    whitelist_info = rate_limit_manager.whitelist.get_whitelist()
    for ip in whitelist_info["individual_ips"]:
        print(f"- {ip}")
    for cidr in whitelist_info["cidr_ranges"]:
        print(f"- {cidr}")
    print("\n测试接口:")
    print("- GET /api/echo?message=test - 测试速率限制")
    print("- GET /status - 查看当前IP状态")
    print("- GET /admin/stats - 查看全局统计（管理员）")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)