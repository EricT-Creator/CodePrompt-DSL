from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

todos: list[dict] = []
next_id = 1


class TodoCreate(BaseModel):
    title: str
    completed: bool = False


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


@app.post("/todos", status_code=201)
async def create_todo(todo: TodoCreate):
    global next_id
    new_todo = {"id": next_id, "title": todo.title, "completed": todo.completed}
    todos.append(new_todo)
    next_id += 1
    return new_todo


@app.get("/todos")
async def list_todos():
    return todos


@app.get("/todos/{todo_id}")
async def get_todo(todo_id: int):
    for todo in todos:
        if todo["id"] == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, updates: TodoUpdate):
    for todo in todos:
        if todo["id"] == todo_id:
            if updates.title is not None:
                todo["title"] = updates.title
            if updates.completed is not None:
                todo["completed"] = updates.completed
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            todos.pop(i)
            return {"detail": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
