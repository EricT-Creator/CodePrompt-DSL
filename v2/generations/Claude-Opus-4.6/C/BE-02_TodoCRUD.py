from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

_todos: list[dict] = []
_id_seq = 0


class TodoIn(BaseModel):
    title: str
    completed: bool = False


class TodoPatch(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


@app.post("/todos", status_code=201)
async def add_todo(payload: TodoIn):
    global _id_seq
    _id_seq += 1
    entry = {"id": _id_seq, "title": payload.title, "completed": payload.completed}
    _todos.append(entry)
    return entry


@app.get("/todos")
async def list_todos():
    return _todos


@app.get("/todos/{tid}")
async def get_todo(tid: int):
    for t in _todos:
        if t["id"] == tid:
            return t
    raise HTTPException(404, "Not found")


@app.put("/todos/{tid}")
async def update_todo(tid: int, patch: TodoPatch):
    for t in _todos:
        if t["id"] == tid:
            if patch.title is not None:
                t["title"] = patch.title
            if patch.completed is not None:
                t["completed"] = patch.completed
            return t
    raise HTTPException(404, "Not found")


@app.delete("/todos/{tid}")
async def remove_todo(tid: int):
    for i, t in enumerate(_todos):
        if t["id"] == tid:
            _todos.pop(i)
            return {"message": "deleted"}
    raise HTTPException(404, "Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
