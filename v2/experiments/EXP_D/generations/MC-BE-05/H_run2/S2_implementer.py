import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

items = []
logs = []
current_id = 1


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start_time) * 1000, 2)
    log_record = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": elapsed,
    }
    logs.append(log_record)
    print(log_record)
    return response


def validate_item_data(data):
    errors = []
    if "name" not in data or not isinstance(data.get("name"), str):
        errors.append("name: required, must be string")
    if "price" not in data:
        errors.append("price: required")
    elif not isinstance(data["price"], (int, float)):
        errors.append("price: must be a number")
    elif data["price"] <= 0:
        errors.append("price: must be > 0")
    if "category" not in data or not isinstance(data.get("category"), str):
        errors.append("category: required, must be string")
    return errors


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global current_id
    body = await request.json()
    errs = validate_item_data(body)
    if errs:
        return JSONResponse(status_code=422, content={"errors": errs})
    item = {
        "id": current_id,
        "name": body["name"],
        "price": body["price"],
        "category": body["category"],
    }
    current_id += 1
    items.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def get_all_items():
    return items


@app.get("/items/{item_id}")
async def get_item_by_id(item_id: int):
    for item in items:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_item(item_id: int, request: Request):
    body = await request.json()
    for item in items:
        if item["id"] == item_id:
            if "name" in body and isinstance(body["name"], str):
                item["name"] = body["name"]
            if "price" in body and isinstance(body["price"], (int, float)):
                item["price"] = body["price"]
            if "category" in body and isinstance(body["category"], str):
                item["category"] = body["category"]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    for idx, item in enumerate(items):
        if item["id"] == item_id:
            items.pop(idx)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level:
        return [l for l in logs if l["level"] == level]
    return logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
