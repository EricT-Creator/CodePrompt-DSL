from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
import datetime

app = FastAPI()

class Todo(BaseModel):
    id: int
    text: str
    completed: bool = False

class TodoCreate(BaseModel):
    text: str
    completed: bool = False

class TodoUpdate(BaseModel):
    text: str | None = None
    completed: bool | None = None

todos: List[Todo] = []
next_id = 1

@app.post("/todos")
async def create_todo(todo: TodoCreate):
    global next_id
    new_todo = Todo(id=next_id, text=todo.text, completed=todo.completed)
    todos.append(new_todo)
    next_id += 1
    return new_todo

@app.get("/todos")
async def get_todos():
    return todos

@app.get("/todos/{todo_id}")
async def get_todo(todo_id: int):
    for todo in todos:
        if todo.id == todo_id:
            return todo
    return {"detail": "未找到"}

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            if todo_update.text is not None:
                todos[i].text = todo_update.text
            if todo_update.completed is not None:
                todos[i].completed = todo_update.completed
            return todos[i]
    return {"detail": "未找到"}

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    global todos
    todos = [todo for todo in todos if todo.id != todo_id]
    return {"message": "已删除"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)