import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

items_store = []
log_entries = []
_id_counter = 1


@app.middleware("http")
async def request_logger(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - t0) * 1000, 2)
    level = "ERROR" if response.status_code >= 400 else "INFO"
    log = {
        "level": level,
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": duration_ms,
    }
    log_entries.append(log)
    print(log)
    return response


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global _id_counter
    body = await request.json()
    errors = []
    if "name" not in body:
        errors.append("name is required")
    elif not isinstance(body["name"], str):
        errors.append("name must be a string")
    if "price" not in body:
        errors.append("price is required")
    elif not isinstance(body["price"], (int, float)):
        errors.append("price must be a number")
    elif body["price"] <= 0:
        errors.append("price must be greater than zero")
    if "category" not in body:
        errors.append("category is required")
    elif not isinstance(body["category"], str):
        errors.append("category must be a string")
    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})
    item = {
        "id": _id_counter,
        "name": body["name"],
        "price": body["price"],
        "category": body["category"],
    }
    _id_counter += 1
    items_store.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def list_all_items():
    return items_store


@app.get("/items/{item_id}")
async def get_single_item(item_id: int):
    for item in items_store:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_existing_item(item_id: int, request: Request):
    body = await request.json()
    for item in items_store:
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
async def remove_item(item_id: int):
    for i, item in enumerate(items_store):
        if item["id"] == item_id:
            items_store.pop(i)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level:
        filtered = [e for e in log_entries if e["level"] == level]
        return filtered
    return log_entries


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
