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
next_id = 1

@app.post("/todos", status_code=201)
def create_todo(todo: TodoCreate):
    global next_id
    item = {"id": next_id, "title": todo.title, "completed": todo.completed}
    todos_db.append(item)
    next_id += 1
    return item

@app.get("/todos")
def list_todos():
    return todos_db

@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    for todo in todos_db:
        if todo["id"] == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo: TodoUpdate):
    for todo in todos_db:
        if todo["id"] == todo_id:
            if todo.title is not None:
                todo["title"] = todo.title
            if todo.completed is not None:
                todo["completed"] = todo.completed
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    for i, todo in enumerate(todos_db):
        if todo["id"] == todo_id:
            todos_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Todo not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
