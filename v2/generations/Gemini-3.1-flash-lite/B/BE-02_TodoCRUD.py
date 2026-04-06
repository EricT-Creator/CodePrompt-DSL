from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
todos = []

class Todo(BaseModel):
    id: int
    text: str
    done: bool = False

@app.post("/todos", response_model=Todo)
def add(text: str):
    todo = Todo(id=len(todos)+1, text=text)
    todos.append(todo)
    return todo

@app.get("/todos")
def get_all():
    return todos

@app.get("/todos/{id}", response_model=Todo)
def get_one(id: int):
    for t in todos:
        if t.id == id: return t
    raise HTTPException(404)

@app.put("/todos/{id}", response_model=Todo)
def update(id: int, done: bool):
    for t in todos:
        if t.id == id:
            t.done = done
            return t
    raise HTTPException(404)

@app.delete("/todos/{id}")
def delete(id: int):
    global todos
    todos = [t for t in todos if t.id != id]
    return {"message": "ok"}
