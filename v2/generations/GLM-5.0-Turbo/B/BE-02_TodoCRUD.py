from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class TodoCreate(BaseModel):
    title: str
    completed: bool = False

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None

todos_db: list[dict] = []
_id_counter = 0

def _next_id():
    global _id_counter
    _id_counter += 1
    return _id_counter

@app.post("/todos", status_code=201)
def create_todo(body: TodoCreate):
    new_id = _next_id()
    record = {"id": new_id, "title": body.title, "completed": body.completed}
    todos_db.append(record)
    return record

@app.get("/todos")
def get_all_todos():
    return todos_db

@app.get("/todos/{item_id}")
def get_single_todo(item_id: int):
    for item in todos_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Todo {item_id} not found")

@app.put("/todos/{item_id}")
def modify_todo(item_id: int, body: TodoUpdate):
    for item in todos_db:
        if item["id"] == item_id:
            update_data = body.model_dump(exclude_unset=True)
            item.update(update_data)
            return item
    raise HTTPException(status_code=404, detail=f"Todo {item_id} not found")

@app.delete("/todos/{item_id}", status_code=204)
def remove_todo(item_id: int):
    for idx in range(len(todos_db)):
        if todos_db[idx]["id"] == item_id:
            todos_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Todo {item_id} not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
