from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class Todo(TodoCreate):
    id: int

todos: List[Todo] = []
current_id = 1

@app.post("/todos", response_model=Todo, status_code=201)
async def create_todo(todo_in: TodoCreate):
    global current_id
    new_todo = Todo(id=current_id, **todo_in.dict())
    todos.append(new_todo)
    current_id += 1
    return new_todo

@app.get("/todos", response_model=List[Todo])
async def get_todos():
    return todos

@app.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(todo_id: int):
    for todo in todos:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, todo_in: TodoCreate):
    for index, todo in enumerate(todos):
        if todo.id == todo_id:
            updated_todo = Todo(id=todo_id, **todo_in.dict())
            todos[index] = updated_todo
            return updated_todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: int):
    for index, todo in enumerate(todos):
        if todo.id == todo_id:
            del todos[index]
            return
    raise HTTPException(status_code=404, detail="Todo not found")
