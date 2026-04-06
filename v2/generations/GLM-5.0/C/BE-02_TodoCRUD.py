from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI()

class Todo(BaseModel):
    id: str
    title: str
    completed: bool = False

class TodoCreate(BaseModel):
    title: str

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None

todos_db: List[Todo] = []

@app.post("/todos", status_code=201)
async def create_todo(todo: TodoCreate):
    new_todo = Todo(id=str(uuid.uuid4()), title=todo.title)
    todos_db.append(new_todo)
    return new_todo

@app.get("/todos")
async def get_todos():
    return todos_db

@app.get("/todos/{todo_id}")
async def get_todo(todo_id: str):
    for todo in todos_db:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, todo_update: TodoUpdate):
    for i, todo in enumerate(todos_db):
        if todo.id == todo_id:
            if todo_update.title is not None:
                todos_db[i].title = todo_update.title
            if todo_update.completed is not None:
                todos_db[i].completed = todo_update.completed
            return todos_db[i]
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    for i, todo in enumerate(todos_db):
        if todo.id == todo_id:
            todos_db.pop(i)
            return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")