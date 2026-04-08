import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

items_data = []
log_data = []
_counter = 1


@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    t_start = time.time()
    response = await call_next(request)
    t_end = time.time()
    ms = round((t_end - t_start) * 1000, 2)
    entry = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": ms,
    }
    log_data.append(entry)
    print(entry)
    return response


@app.post("/items", status_code=201)
async def post_item(request: Request):
    global _counter
    data = await request.json()
    errs = []
    if "name" not in data:
        errs.append("missing required field: name")
    elif not isinstance(data["name"], str):
        errs.append("name must be a string")
    if "price" not in data:
        errs.append("missing required field: price")
    elif not isinstance(data["price"], (int, float)):
        errs.append("price must be numeric")
    elif data["price"] <= 0:
        errs.append("price must be greater than 0")
    if "category" not in data:
        errs.append("missing required field: category")
    elif not isinstance(data["category"], str):
        errs.append("category must be a string")
    if errs:
        return JSONResponse(status_code=422, content={"errors": errs})
    item = {
        "id": _counter,
        "name": data["name"],
        "price": data["price"],
        "category": data["category"],
    }
    _counter += 1
    items_data.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def get_items():
    return items_data


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in items_data:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def put_item(item_id: int, request: Request):
    data = await request.json()
    for item in items_data:
        if item["id"] == item_id:
            if "name" in data:
                item["name"] = data["name"]
            if "price" in data:
                item["price"] = data["price"]
            if "category" in data:
                item["category"] = data["category"]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def del_item(item_id: int):
    for i, item in enumerate(items_data):
        if item["id"] == item_id:
            items_data.pop(i)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def get_logs(level: str = None):
    if level is not None:
        return [e for e in log_data if e["level"] == level]
    return log_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
