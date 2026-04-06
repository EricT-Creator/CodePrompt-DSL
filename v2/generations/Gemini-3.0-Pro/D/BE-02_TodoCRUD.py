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

# 内存列表存储
todos_db: List[Todo] = []
current_id = 1

@app.post("/todos", response_model=Todo, status_code=201)
def create_todo(todo_in: TodoCreate):
    global current_id
    new_todo = Todo(id=current_id, **todo_in.dict())
    todos_db.append(new_todo)
    current_id += 1
    return new_todo

@app.get("/todos", response_model=List[Todo])
def read_todos():
    return todos_db

@app.get("/todos/{id}", response_model=Todo)
def read_todo(id: int):
    for todo in todos_db:
        if todo.id == id:
            return todo
    raise HTTPException(status_code=404, detail="待办未寻得")

@app.put("/todos/{id}", response_model=Todo)
def update_todo(id: int, todo_in: TodoCreate):
    for index, todo in enumerate(todos_db):
        if todo.id == id:
            updated_todo = Todo(id=id, **todo_in.dict())
            todos_db[index] = updated_todo
            return updated_todo
    raise HTTPException(status_code=404, detail="待办未寻得")

@app.delete("/todos/{id}", status_code=204)
def delete_todo(id: int):
    for index, todo in enumerate(todos_db):
        if todo.id == id:
            del todos_db[index]
            return
    raise HTTPException(status_code=404, detail="待办未寻得")
