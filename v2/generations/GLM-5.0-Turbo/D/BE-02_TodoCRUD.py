from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class CreateTodo(BaseModel):
    title: str
    completed: bool = False

class ModifyTodo(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None

todo_list: list[dict] = []
_seq = 0

def _gen_id():
    global _seq
    _seq += 1
    return _seq

@app.post("/todos", status_code=201)
def create_todo(data: CreateTodo):
    uid = _gen_id()
    item = {"id": uid, "title": data.title, "completed": data.completed}
    todo_list.append(item)
    return item

@app.get("/todos")
def read_all():
    return todo_list

@app.get("/todos/{uid}")
def read_one(uid: int):
    for item in todo_list:
        if item["id"] == uid:
            return item
    raise HTTPException(status_code=404, detail="该待办不存在")

@app.put("/todos/{uid}")
def update_todo(uid: int, data: ModifyTodo):
    for item in todo_list:
        if item["id"] == uid:
            if data.title is not None:
                item["title"] = data.title
            if data.completed is not None:
                item["completed"] = data.completed
            return item
    raise HTTPException(status_code=404, detail="该待办不存在")

@app.delete("/todos/{uid}", status_code=204)
def delete_todo(uid: int):
    for i, item in enumerate(todo_list):
        if item["id"] == uid:
            todo_list.pop(i)
            return
    raise HTTPException(status_code=404, detail="该待办不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
