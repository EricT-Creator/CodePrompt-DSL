import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

items_db = []
request_logs = []
next_item_id = 1


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = round((time.time() - start) * 1000, 2)
    log_level = "ERROR" if response.status_code >= 400 else "INFO"
    entry = {
        "level": log_level,
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": elapsed_ms,
    }
    request_logs.append(entry)
    print(entry)
    return response


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global next_item_id
    data = await request.json()
    validation_errors = []
    if not isinstance(data.get("name"), str):
        validation_errors.append("name must be a non-empty string")
    if not isinstance(data.get("price"), (int, float)):
        validation_errors.append("price must be a number")
    elif data["price"] <= 0:
        validation_errors.append("price must be positive")
    if not isinstance(data.get("category"), str):
        validation_errors.append("category must be a string")
    if validation_errors:
        return JSONResponse(status_code=422, content={"errors": validation_errors})
    new_item = {
        "id": next_item_id,
        "name": data["name"],
        "price": data["price"],
        "category": data["category"],
    }
    next_item_id += 1
    items_db.append(new_item)
    return JSONResponse(status_code=201, content=new_item)


@app.get("/items")
async def list_items():
    return items_db


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_item(item_id: int, request: Request):
    data = await request.json()
    for item in items_db:
        if item["id"] == item_id:
            for field in ("name", "price", "category"):
                if field in data:
                    item[field] = data[field]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    for idx, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(idx)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level is not None:
        return [entry for entry in request_logs if entry["level"] == level]
    return request_logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
