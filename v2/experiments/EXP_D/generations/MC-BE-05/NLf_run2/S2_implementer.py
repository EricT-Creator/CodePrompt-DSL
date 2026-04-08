import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

all_items = []
all_logs = []
auto_id = 1


@app.middleware("http")
async def middleware_logger(request: Request, call_next):
    begin = time.time()
    response = await call_next(request)
    time_ms = round((time.time() - begin) * 1000, 2)
    log_dict = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": time_ms,
    }
    all_logs.append(log_dict)
    print(log_dict)
    return response


@app.post("/items", status_code=201)
async def create(request: Request):
    global auto_id
    payload = await request.json()
    err = []
    if "name" not in payload or not isinstance(payload.get("name"), str):
        err.append("field 'name' required as string")
    if "price" not in payload or not isinstance(payload.get("price"), (int, float)):
        err.append("field 'price' required as number")
    elif payload.get("price", 0) <= 0:
        err.append("field 'price' must be > 0")
    if "category" not in payload or not isinstance(payload.get("category"), str):
        err.append("field 'category' required as string")
    if err:
        return JSONResponse(status_code=422, content={"errors": err})
    record = {
        "id": auto_id,
        "name": payload["name"],
        "price": payload["price"],
        "category": payload["category"],
    }
    auto_id += 1
    all_items.append(record)
    return JSONResponse(status_code=201, content=record)


@app.get("/items")
async def read_all():
    return all_items


@app.get("/items/{item_id}")
async def read_one(item_id: int):
    for it in all_items:
        if it["id"] == item_id:
            return it
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update(item_id: int, request: Request):
    payload = await request.json()
    for it in all_items:
        if it["id"] == item_id:
            for k in ("name", "price", "category"):
                if k in payload:
                    it[k] = payload[k]
            return it
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete(item_id: int):
    for idx, it in enumerate(all_items):
        if it["id"] == item_id:
            all_items.pop(idx)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def logs(level: str = None):
    if level:
        return [x for x in all_logs if x["level"] == level]
    return all_logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
