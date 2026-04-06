from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Todo(BaseModel):
    id: int
    text: str
    completed: bool = False

todos = []

@app.post("/todos", response_model=Todo)
def create(text: str):
    new_todo = Todo(id=len(todos) + 1, text=text)
    todos.append(new_todo)
    return new_todo

@app.get("/todos", response_model=List[Todo])
def get_all():
    return todos

@app.get("/todos/{id}", response_model=Todo)
def get_one(id: int):
    for t in todos:
        if t.id == id: return t
    raise HTTPException(status_code=404)

@app.put("/todos/{id}", response_model=Todo)
def update(id: int, completed: bool):
    for t in todos:
        if t.id == id:
            t.completed = completed
            return t
    raise HTTPException(status_code=404)

@app.delete("/todos/{id}")
def delete(id: int):
    global todos
    todos = [t for t in todos if t.id != id]
    return {"message": "deleted"}
