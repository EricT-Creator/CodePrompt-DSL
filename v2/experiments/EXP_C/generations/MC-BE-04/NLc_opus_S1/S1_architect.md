# Technical Design Document — Token Bucket Rate Limiter Middleware

## 1. Overview

A FastAPI middleware implementing the Token Bucket algorithm for per-IP rate limiting. Returns HTTP 429 with a `Retry-After` header when a client exceeds its rate limit. Supports an IP whitelist that bypasses rate limiting entirely.

## 2. Token Bucket Algorithm Details

### Concept
Each client (identified by IP address) has a virtual "bucket" that holds tokens. Tokens are added at a constant rate up to a maximum burst capacity. Each request consumes one token. If the bucket is empty, the request is rejected.

### Parameters
- **rate**: tokens added per second (e.g., 10.0).
- **burst**: maximum bucket capacity (e.g., 20). Allows short bursts above the sustained rate.

### State Per Bucket
- `tokens: float` — current token count.
- `last_refill: float` — timestamp of the last refill calculation.

### Refill Calculation (lazy refill)
Rather than running a background timer, tokens are refilled lazily on each request:

```
now = time.time()
elapsed = now - bucket.last_refill
bucket.tokens = min(burst, bucket.tokens + elapsed * rate)
bucket.last_refill = now
```

### Token Consumption
After refill:
- If `bucket.tokens >= 1.0`: decrement by 1.0, allow request.
- If `bucket.tokens < 1.0`: reject request with 429.

### Advantages
- O(1) per request — no background tasks or timers.
- Naturally handles burst traffic (up to `burst` requests can arrive simultaneously).
- Smooth rate limiting without hard time-window edges.

## 3. Per-IP Bucket Management

### Data Structure
```python
buckets: dict[str, TokenBucket]
```

- Key: client IP address string.
- Value: `TokenBucket` instance (`tokens`, `last_refill`).

### IP Extraction
- From `request.client.host` (FastAPI/Starlette provides this).
- For production behind a reverse proxy, one would use `X-Forwarded-For`, but for this single-file scope, `client.host` suffices.

### Lazy Initialization
- On first request from a new IP, create a bucket with `tokens = burst` (full bucket).
- Store it in the `buckets` dict.

### Memory Cleanup (optional)
- A periodic cleanup can evict buckets not accessed for > N minutes.
- For this single-file design, a simple check during request processing suffices: if `elapsed > cleanup_threshold`, remove stale entries. This prevents unbounded memory growth from unique IPs.

## 4. Middleware Integration

### FastAPI Middleware Pattern
```python
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    if ip in whitelist:
        return await call_next(request)

    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume()

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after)}
        )

    return await call_next(request)
```

### Execution Order
1. Extract client IP.
2. Check whitelist → bypass if listed.
3. Get or create the IP's bucket.
4. Lazy refill tokens.
5. Attempt to consume one token.
6. If denied, return 429 with `Retry-After`.
7. If allowed, call the next handler.

## 5. Retry-After Calculation

When a request is rejected (tokens < 1.0):

```
deficit = 1.0 - bucket.tokens
retry_after = math.ceil(deficit / rate)
```

This tells the client how many seconds to wait until at least one token will be available. The value is returned as an integer (whole seconds, rounded up) in the `Retry-After` HTTP header, per RFC 7231 §7.1.3.

## 6. IP Whitelist

### Configuration
```python
WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1", ...}
```

- Stored as a Python `set` for O(1) lookup.
- Configurable at startup (hardcoded for single-file scope; a production system would load from environment variables or config).

### Behavior
- Whitelisted IPs skip the entire token bucket check.
- No bucket is created or maintained for whitelisted IPs.
- The whitelist check is the first operation in the middleware, before any bucket logic.

## 7. API Endpoints (for demonstration)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Simple "Hello" endpoint to test rate limiting |
| `GET` | `/status` | Returns current rate limit config and caller's remaining tokens |

These are example endpoints to demonstrate the middleware in action.

## 8. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python + FastAPI** | FastAPI app with `@app.middleware("http")` integration. |
| 2 | **Token Bucket required, no simple counter** | Full Token Bucket implementation with lazy refill, burst capacity, and fractional token tracking. Not a fixed-window counter or sliding-log approach. |
| 3 | **stdlib + fastapi only, no Redis** | All state is in-process Python dicts. No Redis, Memcached, or external store. Only `fastapi`, `uvicorn`, and stdlib modules (`time`, `math`, `dataclasses`). |
| 4 | **Single file** | All logic — middleware, bucket class, whitelist, endpoints — in one `.py` file. |
| 5 | **429 with Retry-After** | Rejected requests receive HTTP 429 with a calculated `Retry-After` header indicating seconds until a token is available. |
| 6 | **IP whitelist** | A `set[str]` of IPs is checked first in the middleware; matching IPs bypass all rate limiting. |
| 7 | **Code only** | Deliverable is pure Python source code. |
