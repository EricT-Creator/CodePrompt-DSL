from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Todo(BaseModel):
    id: int
    task: str
    completed: bool = False

todos: List[Todo] = []

@app.post("/todos", response_model=Todo, status_code=201)
async def create_todo(todo: Todo):
    todos.append(todo)
    return todo

@app.get("/todos", response_model=List[Todo])
async def read_todos():
    return todos

@app.get("/todos/{id}", response_model=Todo)
async def read_todo(id: int):
    for todo in todos:
        if todo.id == id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{id}", response_model=Todo)
async def update_todo(id: int, updated_todo: Todo):
    for index, todo in enumerate(todos):
        if todo.id == id:
            todos[index] = updated_todo
            return updated_todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{id}", status_code=204)
async def delete_todo(id: int):
    for index, todo in enumerate(todos):
        if todo.id == id:
            todos.pop(index)
            return
    raise HTTPException(status_code=404, detail="Todo not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
