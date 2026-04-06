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

todos_db: List[Todo] = []
current_id = 1

@app.post("/todos", response_model=Todo, status_code=201)
def create_todo(todo: TodoCreate):
    global current_id
    new_todo = Todo(id=current_id, **todo.dict())
    todos_db.append(new_todo)
    current_id += 1
    return new_todo

@app.get("/todos", response_model=List[Todo])
def get_todos():
    return todos_db

@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(todo_id: int):
    for todo in todos_db:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo_update: TodoCreate):
    for index, todo in enumerate(todos_db):
        if todo.id == todo_id:
            updated_todo = Todo(id=todo_id, **todo_update.dict())
            todos_db[index] = updated_todo
            return updated_todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    for index, todo in enumerate(todos_db):
        if todo.id == todo_id:
            del todos_db[index]
            return
    raise HTTPException(status_code=404, detail="Todo not found")
