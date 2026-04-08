import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

inventory = []
access_logs = []
seq_id = 1


@app.middleware("http")
async def print_logger(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    delta_ms = round((time.time() - start) * 1000, 2)
    record = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": delta_ms,
    }
    access_logs.append(record)
    print(record)
    return response


@app.post("/items", status_code=201)
async def create_item(request: Request):
    global seq_id
    body = await request.json()
    issues = []
    if not isinstance(body.get("name"), str):
        issues.append("name: must be a string")
    if not isinstance(body.get("price"), (int, float)):
        issues.append("price: must be a number")
    elif body["price"] <= 0:
        issues.append("price: must be > 0")
    if not isinstance(body.get("category"), str):
        issues.append("category: must be a string")
    if issues:
        return JSONResponse(status_code=422, content={"errors": issues})
    new_item = {
        "id": seq_id,
        "name": body["name"],
        "price": body["price"],
        "category": body["category"],
    }
    seq_id += 1
    inventory.append(new_item)
    return JSONResponse(status_code=201, content=new_item)


@app.get("/items")
async def get_items():
    return inventory


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in inventory:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def update_item(item_id: int, request: Request):
    body = await request.json()
    for item in inventory:
        if item["id"] == item_id:
            for key in ("name", "price", "category"):
                if key in body:
                    item[key] = body[key]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    for i, item in enumerate(inventory):
        if item["id"] == item_id:
            inventory.pop(i)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def query_logs(level: str = None):
    if level:
        return [r for r in access_logs if r["level"] == level]
    return access_logs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
