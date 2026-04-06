from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
import uvicorn

app = FastAPI()

class TodoItem(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TodoItemResponse(TodoItem):
    id: str

todos_db = []

@app.post("/todos", response_model=TodoItemResponse)
async def create_todo(todo: TodoItem):
    todo_id = str(uuid.uuid4())
    new_todo = TodoItemResponse(id=todo_id, **todo.dict())
    todos_db.append(new_todo)
    return new_todo

@app.get("/todos", response_model=List[TodoItemResponse])
async def get_all_todos():
    return todos_db

@app.get("/todos/{todo_id}", response_model=TodoItemResponse)
async def get_todo(todo_id: str):
    for todo in todos_db:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@app.put("/todos/{todo_id}", response_model=TodoItemResponse)
async def update_todo(todo_id: str, updated_todo: TodoItem):
    for i, todo in enumerate(todos_db):
        if todo.id == todo_id:
            updated = TodoItemResponse(id=todo_id, **updated_todo.dict())
            todos_db[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    for i, todo in enumerate(todos_db):
        if todo.id == todo_id:
            del todos_db[i]
            return {"message": "Todo deleted successfully"}
    raise HTTPException(status_code=404, detail="Todo not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)