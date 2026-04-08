import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

items = []
logs = []
_next_id = 1


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response_time_ms = round((time.time() - start_time) * 1000, 2)
    level = "ERROR" if response.status_code >= 400 else "INFO"
    log_entry = {
        "level": level,
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": response_time_ms,
    }
    logs.append(log_entry)
    print(log_entry)
    return response


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global _next_id
    body = await request.json()
    errors = []
    if "name" not in body or not isinstance(body.get("name"), str):
        errors.append("name is required and must be a string")
    if "price" not in body or not isinstance(body.get("price"), (int, float)):
        errors.append("price is required and must be a number")
    elif body["price"] <= 0:
        errors.append("price must be greater than 0")
    if "category" not in body or not isinstance(body.get("category"), str):
        errors.append("category is required and must be a string")
    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})
    item = {
        "id": _next_id,
        "name": body["name"],
        "price": body["price"],
        "category": body["category"],
    }
    _next_id += 1
    items.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def get_items():
    return items


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in items:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_item(item_id: int, request: Request):
    body = await request.json()
    for item in items:
        if item["id"] == item_id:
            if "name" in body:
                item["name"] = body["name"]
            if "price" in body:
                item["price"] = body["price"]
            if "category" in body:
                item["category"] = body["category"]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    for i, item in enumerate(items):
        if item["id"] == item_id:
            items.pop(i)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level:
        return [log for log in logs if log["level"] == level]
    return logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
