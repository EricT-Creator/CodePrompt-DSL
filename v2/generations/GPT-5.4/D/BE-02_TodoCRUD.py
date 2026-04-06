from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()


class TodoPayload(BaseModel):
    title: str
    completed: bool = False


items: list[dict[str, object]] = []


def find_item(todo_id: int) -> dict[str, object]:
    for item in items:
        if item["id"] == todo_id:
            return item
    raise HTTPException(status_code=404, detail="Todo not found")


@app.post("/todos", status_code=status.HTTP_201_CREATED)
def create(payload: TodoPayload) -> dict[str, object]:
    todo = {
        "id": (items[-1]["id"] + 1) if items else 1,
        "title": payload.title,
        "completed": payload.completed,
    }
    items.append(todo)
    return todo


@app.get("/todos")
def all_todos() -> list[dict[str, object]]:
    return items


@app.get("/todos/{todo_id}")
def one_todo(todo_id: int) -> dict[str, object]:
    return find_item(todo_id)


@app.put("/todos/{todo_id}")
def change(todo_id: int, payload: TodoPayload) -> dict[str, object]:
    todo = find_item(todo_id)
    todo.update({"title": payload.title, "completed": payload.completed})
    return todo


@app.delete("/todos/{todo_id}")
def remove(todo_id: int) -> dict[str, object]:
    todo = find_item(todo_id)
    items.remove(todo)
    return {"deleted": True, "id": todo_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
