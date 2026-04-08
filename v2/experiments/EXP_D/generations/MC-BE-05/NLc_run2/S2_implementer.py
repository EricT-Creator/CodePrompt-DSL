import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

item_list = []
log_store = []
id_seq = 1


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    ts = time.time()
    response = await call_next(request)
    ms = round((time.time() - ts) * 1000, 2)
    rec = {
        "level": "ERROR" if response.status_code >= 400 else "INFO",
        "method": request.method,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response_time_ms": ms,
    }
    log_store.append(rec)
    print(rec)
    return response


@app.post("/items", status_code=201)
async def add_item(request: Request):
    global id_seq
    raw = await request.json()
    problems = []
    if not isinstance(raw.get("name"), str):
        problems.append("name is required as a string")
    if not isinstance(raw.get("price"), (int, float)):
        problems.append("price is required as a number")
    elif raw["price"] <= 0:
        problems.append("price must be positive")
    if not isinstance(raw.get("category"), str):
        problems.append("category is required as a string")
    if problems:
        return JSONResponse(status_code=422, content={"errors": problems})
    item = {"id": id_seq, "name": raw["name"], "price": raw["price"], "category": raw["category"]}
    id_seq += 1
    item_list.append(item)
    return JSONResponse(status_code=201, content=item)


@app.get("/items")
async def list_items():
    return item_list


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    for item in item_list:
        if item["id"] == item_id:
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.put("/items/{item_id}")
async def modify_item(item_id: int, request: Request):
    raw = await request.json()
    for item in item_list:
        if item["id"] == item_id:
            for key in ("name", "price", "category"):
                if key in raw:
                    item[key] = raw[key]
            return item
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.delete("/items/{item_id}", status_code=204)
async def remove_item(item_id: int):
    for i, item in enumerate(item_list):
        if item["id"] == item_id:
            item_list.pop(i)
            return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=404, content={"detail": "Item not found"})


@app.get("/logs")
async def fetch_logs(level: str = None):
    if level:
        return [r for r in log_store if r["level"] == level]
    return log_store


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
