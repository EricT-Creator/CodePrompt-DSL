from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
data = []

class Todo(BaseModel):
    id: int
    title: str

@app.post("/todos")
async def add(t: Todo):
    data.append(t)
    return t

@app.get("/todos")
async def all():
    return data

@app.get("/todos/{id}")
async def one(id: int):
    res = next((x for x in data if x.id == id), None)
    if not res: raise HTTPException(404)
    return res

@app.put("/todos/{id}")
async def up(id: int, t: Todo):
    for i, x in enumerate(data):
        if x.id == id:
            data[i] = t
            return t
    raise HTTPException(404)

@app.delete("/todos/{id}")
async def rem(id: int):
    global data
    data = [x for x in data if x.id != id]
    return {"ok": True}
