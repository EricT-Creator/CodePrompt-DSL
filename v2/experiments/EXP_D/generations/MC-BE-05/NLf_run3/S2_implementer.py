import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

item_registry = []
log_registry = []
next_id = 1


@app.middleware("http")
async def capture_request_log(request: Request, call_next):
    now = time.time()
    response = await call_next(request)
    resp_ms = round((time.time() - now) * 1000, 2)
    log_obj = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": resp_ms,
    }
    log_registry.append(log_obj)
    print(log_obj)
    return response


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global next_id
    raw = await request.json()
    validation_msgs = []
    if "name" not in raw or not isinstance(raw.get("name"), str):
        validation_msgs.append("name is required and must be string")
    if "price" not in raw or not isinstance(raw.get("price"), (int, float)):
        validation_msgs.append("price is required and must be numeric")
    elif raw["price"] <= 0:
        validation_msgs.append("price must be positive")
    if "category" not in raw or not isinstance(raw.get("category"), str):
        validation_msgs.append("category is required and must be string")
    if validation_msgs:
        return JSONResponse(status_code=422, content={"errors": validation_msgs})
    item = {
        "id": next_id,
        "name": raw["name"],
        "price": raw["price"],
        "category": raw["category"],
    }
    next_id += 1
    item_registry.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def list_items():
    return item_registry


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in item_registry:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_item(item_id: int, request: Request):
    raw = await request.json()
    for item in item_registry:
        if item["id"] == item_id:
            if "name" in raw:
                item["name"] = raw["name"]
            if "price" in raw:
                item["price"] = raw["price"]
            if "category" in raw:
                item["category"] = raw["category"]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    for idx, item in enumerate(item_registry):
        if item["id"] == item_id:
            item_registry.pop(idx)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level is not None:
        return [entry for entry in log_registry if entry["level"] == level]
    return log_registry


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
