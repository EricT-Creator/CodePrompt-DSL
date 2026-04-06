from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()
router = APIRouter()


class TodoIn(BaseModel):
    title: str
    completed: bool = False


class TodoStore:
    def __init__(self) -> None:
        self._items: list[dict[str, object]] = []
        self._next_id = 1

    def create(self, payload: TodoIn) -> dict[str, object]:
        item = {"id": self._next_id, "title": payload.title, "completed": payload.completed}
        self._next_id += 1
        self._items.append(item)
        return item

    def list_all(self) -> list[dict[str, object]]:
        return list(self._items)

    def get(self, todo_id: int) -> dict[str, object]:
        for item in self._items:
            if item["id"] == todo_id:
                return item
        raise HTTPException(status_code=404, detail="Todo not found")

    def update(self, todo_id: int, payload: TodoIn) -> dict[str, object]:
        item = self.get(todo_id)
        item["title"] = payload.title
        item["completed"] = payload.completed
        return item

    def delete(self, todo_id: int) -> None:
        for index, item in enumerate(self._items):
            if item["id"] == todo_id:
                self._items.pop(index)
                return
        raise HTTPException(status_code=404, detail="Todo not found")


store = TodoStore()


@router.post("/todos", status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoIn) -> dict[str, object]:
    return store.create(payload)


@router.get("/todos")
def list_todos() -> list[dict[str, object]]:
    return store.list_all()


@router.get("/todos/{todo_id}")
def read_todo(todo_id: int) -> dict[str, object]:
    return store.get(todo_id)


@router.put("/todos/{todo_id}")
def update_todo(todo_id: int, payload: TodoIn) -> dict[str, object]:
    return store.update(todo_id, payload)


@router.delete("/todos/{todo_id}")
def delete_todo(todo_id: int) -> dict[str, bool]:
    store.delete(todo_id)
    return {"deleted": True}


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
