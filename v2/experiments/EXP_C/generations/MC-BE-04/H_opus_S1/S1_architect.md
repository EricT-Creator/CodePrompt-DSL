# Technical Design Document: Rate Limiter Middleware

**Task**: MC-BE-04  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]Python [F]FastAPI [ALGO]TOKEN_BUCKET [!A]NO_COUNTER [D]STDLIB+FASTAPI [!D]NO_REDIS [O]SINGLE_FILE [RESP]429_RETRY_AFTER [WL]IP [OUT]CODE_ONLY`

---

## 1. Token Bucket Algorithm Details

### Core Concept

Each client (identified by IP) has a virtual "bucket" that holds tokens. Tokens are consumed on each request and refill at a steady rate over time.

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rate` | Tokens added per second | 10 |
| `burst` | Maximum bucket capacity | 20 |

### Algorithm Steps (per request)

```
1. Look up bucket for this IP
2. Calculate elapsed time since last request
3. Refill: tokens = min(tokens + elapsed * rate, burst)
4. If tokens >= 1.0:
     tokens -= 1.0
     ALLOW request
5. Else:
     Calculate wait_time = (1.0 - tokens) / rate
     DENY request → 429 with Retry-After: ceil(wait_time)
```

### Token Refill Model

Tokens are not refilled by a background timer. Instead, they are **lazily refilled** on each request by calculating how many tokens should have accumulated since the last access:

```
elapsed = current_time - bucket.last_access
bucket.tokens = min(bucket.tokens + elapsed * rate, burst)
bucket.last_access = current_time
```

This lazy approach avoids the need for background tasks or timers and works purely within the request lifecycle.

---

## 2. Per-IP Bucket Management

### Data Structure

```python
@dataclass
class TokenBucket:
    tokens: float           # current token count
    last_access: float      # timestamp of last request (time.monotonic())

class BucketStore:
    _buckets: dict[str, TokenBucket]    # IP → bucket
    rate: float                          # tokens per second
    burst: float                         # max capacity

    def get_or_create(self, ip: str) -> TokenBucket: ...
    def consume(self, ip: str) -> tuple[bool, float]: ...
    #  Returns (allowed: bool, retry_after: float)
```

### Bucket Creation

On first request from an IP, a new bucket is created with `tokens = burst` (full bucket). This means the first `burst` requests are always allowed.

### Memory Management

Over time, inactive IPs accumulate buckets. A periodic cleanup can be triggered (e.g., every 1000 requests, scan and remove buckets where `current_time - last_access > 1 hour`). This is a lightweight optimization, not a hard requirement.

### IP Extraction

```python
def get_client_ip(request: Request) -> str:
    # Check X-Forwarded-For for proxied requests
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host
```

---

## 3. Middleware Integration

### FastAPI Middleware Approach

```python
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)

    # Check whitelist
    if client_ip in IP_WHITELIST:
        return await call_next(request)

    # Consume token
    allowed, retry_after = bucket_store.consume(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(math.ceil(retry_after))}
        )

    response = await call_next(request)

    # Add rate limit headers to successful responses
    bucket = bucket_store.get_or_create(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))

    return response
```

### Middleware Position

The rate limiter middleware is registered **first** (outermost), so it intercepts all requests before any route handler or other middleware executes. This ensures even malformed requests are rate-limited.

### Informational Headers

Successful responses include:
- `X-RateLimit-Remaining`: Current tokens left (floored to integer).
- `X-RateLimit-Limit`: Maximum burst capacity.

---

## 4. Retry-After Calculation

### Formula

When a request is denied (tokens < 1.0):

```
deficit = 1.0 - current_tokens
retry_after_seconds = deficit / rate
```

This tells the client exactly how long to wait before the bucket will have accumulated enough tokens for one request.

### Example

- `rate = 10` tokens/sec, `burst = 20`
- Client has `tokens = 0.3`
- `deficit = 1.0 - 0.3 = 0.7`
- `retry_after = 0.7 / 10 = 0.07 seconds` → `Retry-After: 1` (ceiling to integer)

### HTTP Response

```
HTTP/1.1 429 Too Many Requests
Retry-After: 1
Content-Type: application/json

{"detail": "Rate limit exceeded"}
```

The `Retry-After` header value is always an integer (ceiling of the calculated seconds), per HTTP specification.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: Python | `[L]Python` | Entire implementation in Python 3.10+. |
| Framework: FastAPI | `[F]FastAPI` | Middleware registered via `@app.middleware("http")`. Routes and models use FastAPI patterns. |
| Algorithm: Token Bucket | `[ALGO]TOKEN_BUCKET` | Full token bucket with lazy refill, configurable rate and burst. Not sliding window, not fixed window. |
| No simple counter | `[!A]NO_COUNTER` | No naive request counting per time window. Token bucket with continuous refill is used. |
| Dependencies: stdlib + FastAPI | `[D]STDLIB+FASTAPI` | Only `time`, `math`, `dataclasses` from stdlib. FastAPI/Starlette for HTTP handling. |
| No Redis | `[!D]NO_REDIS` | No Redis, no external store. All buckets stored in-memory `dict`. |
| Single file | `[O]SINGLE_FILE` | All logic (bucket store, middleware, routes, IP extraction) in one `.py` file. |
| Response: 429 with Retry-After | `[RESP]429_RETRY_AFTER` | Denied requests return HTTP 429 with `Retry-After` header calculated from token deficit. |
| Whitelist by IP | `[WL]IP` | `IP_WHITELIST: set[str]` checked before token consumption. Whitelisted IPs bypass rate limiting entirely. |
| Code only output | `[OUT]CODE_ONLY` | Final S2 deliverable will be pure code. |
