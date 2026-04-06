from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Todo(BaseModel):
    id: Optional[int] = None
    title: str
    completed: bool = False

todos = []
next_id = 1

@app.post("/todos")
def create_todo(todo: Todo):
    global next_id
    todo.id = next_id
    next_id += 1
    todos.append(todo)
    return todo

@app.get("/todos")
def list_todos():
    return todos

@app.get("/todos/{id}")
def get_todo(id: int):
    for todo in todos:
        if todo.id == id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{id}")
def update_todo(id: int, updated: Todo):
    for i, todo in enumerate(todos):
        if todo.id == id:
            todos[i] = updated
            todos[i].id = id
            return todos[i]
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{id}")
def delete_todo(id: int):
    for i, todo in enumerate(todos):
        if todo.id == id:
            todos.pop(i)
            return {"deleted": id}
    raise HTTPException(status_code=404, detail="Todo not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
