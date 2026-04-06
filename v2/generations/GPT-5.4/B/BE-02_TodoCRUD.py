from itertools import count

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Todo CRUD API")


class CreateTodoBody(BaseModel):
    title: str
    completed: bool = False


class UpdateTodoBody(BaseModel):
    title: str
    completed: bool


store: dict[int, dict[str, object]] = {}
id_counter = count(1)


@app.post("/todos", status_code=status.HTTP_201_CREATED)
def create_todo(body: CreateTodoBody) -> dict[str, object]:
    todo_id = next(id_counter)
    todo = {"id": todo_id, "title": body.title, "completed": body.completed}
    store[todo_id] = todo
    return todo


@app.get("/todos")
def get_all_todos() -> list[dict[str, object]]:
    return [store[key] for key in sorted(store)]


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int) -> dict[str, object]:
    todo = store.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@app.put("/todos/{todo_id}")
def replace_todo(todo_id: int, body: UpdateTodoBody) -> dict[str, object]:
    if todo_id not in store:
        raise HTTPException(status_code=404, detail="Todo not found")
    updated = {"id": todo_id, "title": body.title, "completed": body.completed}
    store[todo_id] = updated
    return updated


@app.delete("/todos/{todo_id}")
def remove_todo(todo_id: int) -> dict[str, object]:
    if todo_id not in store:
        raise HTTPException(status_code=404, detail="Todo not found")
    deleted = store.pop(todo_id)
    return {"deleted": True, "todo": deleted}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
