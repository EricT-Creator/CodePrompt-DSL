from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

todo_list: list[dict] = []
counter = 0


class CreateTodo(BaseModel):
    title: str
    completed: bool = False


class UpdateTodo(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


@app.post("/todos", status_code=201)
async def create_todo(body: CreateTodo):
    global counter
    counter += 1
    todo = {"id": counter, "title": body.title, "completed": body.completed}
    todo_list.append(todo)
    return todo


@app.get("/todos")
async def get_all_todos():
    return todo_list


@app.get("/todos/{todo_id}")
async def get_todo(todo_id: int):
    for item in todo_list:
        if item["id"] == todo_id:
            return item
    raise HTTPException(status_code=404, detail="Todo not found")


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, body: UpdateTodo):
    for item in todo_list:
        if item["id"] == todo_id:
            if body.title is not None:
                item["title"] = body.title
            if body.completed is not None:
                item["completed"] = body.completed
            return item
    raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    for idx, item in enumerate(todo_list):
        if item["id"] == todo_id:
            removed = todo_list.pop(idx)
            return {"detail": "Deleted", "todo": removed}
    raise HTTPException(status_code=404, detail="Todo not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
