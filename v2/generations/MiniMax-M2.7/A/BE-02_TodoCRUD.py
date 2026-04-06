from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Todo(BaseModel):
    title: str
    completed: bool = False

todos = []
next_id = 1

@app.post("/todos", status_code=201)
def create_todo(todo: Todo):
    global next_id
    item = {"id": next_id, **todo.model_dump()}
    todos.append(item)
    next_id += 1
    return item

@app.get("/todos")
def list_todos():
    return todos

@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    for t in todos:
        if t["id"] == todo_id:
            return t
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo: Todo):
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[i] = {"id": todo_id, **todo.model_dump()}
            return todos[i]
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    global todos
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            todos = todos[:i] + todos[i+1:]
            return
    raise HTTPException(status_code=404, detail="Todo not found")