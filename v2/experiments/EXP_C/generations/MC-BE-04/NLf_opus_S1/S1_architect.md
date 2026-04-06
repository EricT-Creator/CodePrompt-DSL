# Technical Design Document — Token Bucket Rate Limiter Middleware

## 1. Overview

This document describes the architecture for a FastAPI middleware that implements Token Bucket rate limiting on a per-IP basis. The middleware returns HTTP 429 with a Retry-After header when the rate is exceeded and supports an IP whitelist that bypasses rate limiting entirely.

## 2. Token Bucket Algorithm Details

### 2.1 Core Concept

The Token Bucket algorithm controls the rate of requests by maintaining a virtual "bucket" of tokens for each client (identified by IP). Tokens are consumed on each request and replenished at a steady rate.

### 2.2 Parameters

- **rate**: Number of tokens added per second (sustained throughput).
- **burst**: Maximum number of tokens the bucket can hold (peak capacity).

### 2.3 Algorithm

For each incoming request from IP `addr`:

1. Retrieve the bucket for `addr` (or create a new one at full capacity).
2. Calculate the time elapsed since the last request: `elapsed = now - bucket.last_refill`.
3. Add tokens: `bucket.tokens = min(burst, bucket.tokens + elapsed × rate)`.
4. Update `bucket.last_refill = now`.
5. If `bucket.tokens >= 1.0`: consume one token (`bucket.tokens -= 1.0`), allow the request.
6. If `bucket.tokens < 1.0`: reject with HTTP 429.

### 2.4 Properties

- **Burst handling**: A client can make up to `burst` requests instantly if the bucket is full.
- **Sustained rate**: Over time, the average throughput converges to `rate` requests per second.
- **Fairness**: Each IP has its own independent bucket.

## 3. Per-IP Bucket Management

### 3.1 Data Structures

- **TokenBucket**: `{ tokens: float; last_refill: float; rate: float; burst: int }`
- **BucketStore**: `dict[str, TokenBucket]` — Maps IP addresses to their token buckets.

### 3.2 Bucket Lifecycle

- **Creation**: On the first request from an IP, a new bucket is created with `tokens = burst` (full capacity) and `last_refill = time.monotonic()`.
- **Eviction**: To prevent memory leaks from transient IPs, buckets that have not been accessed for more than 1 hour are periodically evicted. A background `asyncio.Task` runs every 5 minutes to scan and remove stale buckets.

### 3.3 Thread Safety

Since FastAPI runs on an asyncio event loop (single-threaded), concurrent access to the bucket store is not a concern for typical deployments. However, if multiple workers are used, each worker maintains its own bucket store (acceptable for in-memory rate limiting without shared storage).

## 4. Middleware Integration

### 4.1 FastAPI Middleware Approach

The rate limiter is implemented as a Starlette `BaseHTTPMiddleware` subclass (or using the `@app.middleware("http")` decorator).

### 4.2 Request Processing Flow

1. Extract client IP from `request.client.host`.
2. Check if IP is in the whitelist. If yes, proceed to the route handler immediately.
3. Look up or create the token bucket for this IP.
4. Refill tokens based on elapsed time.
5. Attempt to consume one token.
6. If successful: call `await call_next(request)` and return the response, adding rate-limit headers.
7. If rate exceeded: return a `JSONResponse` with status 429 and a `Retry-After` header.

### 4.3 Response Headers

On all responses (both allowed and rejected):

| Header | Value | Condition |
|--------|-------|-----------|
| `X-RateLimit-Limit` | `burst` | Always |
| `X-RateLimit-Remaining` | `floor(tokens)` | Always |
| `X-RateLimit-Reset` | Unix timestamp when bucket will be full | Always |
| `Retry-After` | Seconds until at least 1 token is available | Only on 429 |

## 5. Retry-After Calculation

When a request is rejected (`tokens < 1.0`):

```
deficit = 1.0 - bucket.tokens
wait_seconds = deficit / rate
retry_after = math.ceil(wait_seconds)
```

The `Retry-After` header is set to `retry_after` (an integer number of seconds). This tells the client exactly how long to wait before the bucket will have at least one token available.

## 6. IP Whitelist

### 6.1 Configuration

A set of whitelisted IP addresses is defined at startup:

```
WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1", ...}
```

### 6.2 Bypass Logic

In the middleware, before any bucket logic, the client IP is checked against the whitelist set. If present, the request proceeds directly to the handler with no rate limit check and no rate-limit headers.

### 6.3 Dynamic Updates

Optionally, an admin endpoint (e.g., POST `/admin/whitelist`) can add or remove IPs from the whitelist at runtime. This is a secondary feature and not required by the core specification.

## 7. Configuration Model

- **RateLimitConfig**: `{ rate: float; burst: int; whitelist: set[str]; cleanup_interval: int; bucket_ttl: int }`
- Default values: `rate=10.0` (10 req/s), `burst=20`, `cleanup_interval=300` (5 min), `bucket_ttl=3600` (1 hour).
- Configuration is passed to the middleware at initialization.

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python with FastAPI | Built as FastAPI middleware using Starlette's BaseHTTPMiddleware. |
| 2 | Token Bucket algorithm, not simple counter or fixed window | The implementation uses the token bucket algorithm with continuous token replenishment, burst capacity, and per-request token consumption. No fixed time windows or simple counters. |
| 3 | Only Python stdlib and fastapi, no Redis/memcached | All state is stored in-memory using Python dicts. Time functions use `time.monotonic()`. Math uses `math.ceil()`. No external storage system. |
| 4 | Single Python file | All middleware logic, bucket management, configuration, and cleanup task are in one `.py` file. |
| 5 | HTTP 429 with Retry-After header; IP whitelist bypass | Rejected requests return status 429 with a calculated Retry-After header. Whitelisted IPs skip all rate-limit logic. |
| 6 | Output code only, no explanation text | The final implementation will be pure code. This document is the design artifact. |
