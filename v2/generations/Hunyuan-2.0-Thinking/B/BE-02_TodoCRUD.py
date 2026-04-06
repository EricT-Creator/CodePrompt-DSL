from fastapi import FastAPI
from typing import List, Dict
from pydantic import BaseModel

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

@app.post("/todos", response_model=Todo)
async def create_todo(todo: TodoCreate):
    global next_id
    new_todo = Todo(id=next_id, text=todo.text, completed=todo.completed)
    todos.append(new_todo)
    next_id += 1
    return new_todo

@app.get("/todos", response_model=List[Todo])
async def get_todos():
    return todos

@app.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(todo_id: int):
    for todo in todos:
        if todo.id == todo_id:
            return todo
    return {"detail": "Todo not found"}

@app.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            if todo_update.text is not None:
                todos[i].text = todo_update.text
            if todo_update.completed is not None:
                todos[i].completed = todo_update.completed
            return todos[i]
    return {"detail": "Todo not found"}

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    global todos
    todos = [todo for todo in todos if todo.id != todo_id]
    return {"message": "Todo deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)