from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class TodoIn(BaseModel):
    title: str
    completed: bool = False

class TodoPatch(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None

store: list[dict] = []
auto_id = 1

@app.post("/todos", status_code=201)
def add_todo(payload: TodoIn):
    global auto_id
    entry = {"id": auto_id, "title": payload.title, "completed": payload.completed}
    store.append(entry)
    auto_id += 1
    return entry

@app.get("/todos")
def fetch_all():
    return store

@app.get("/todos/{tid}")
def fetch_one(tid: int):
    for entry in store:
        if entry["id"] == tid:
            return entry
    raise HTTPException(404, "Not found")

@app.put("/todos/{tid}")
def edit_todo(tid: int, payload: TodoPatch):
    for entry in store:
        if entry["id"] == tid:
            if payload.title is not None:
                entry["title"] = payload.title
            if payload.completed is not None:
                entry["completed"] = payload.completed
            return entry
    raise HTTPException(404, "Not found")

@app.delete("/todos/{tid}", status_code=204)
def erase_todo(tid: int):
    for i in range(len(store)):
        if store[i]["id"] == tid:
            store.pop(i)
            return
    raise HTTPException(404, "Not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
