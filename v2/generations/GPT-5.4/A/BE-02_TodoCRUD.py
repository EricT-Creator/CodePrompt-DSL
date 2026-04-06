from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI()


class TodoCreate(BaseModel):
    title: str


class TodoUpdate(BaseModel):
    title: str
    completed: bool


class TodoItem(TodoUpdate):
    id: int


todos: list[TodoItem] = []
next_id = 1


@app.post("/todos", response_model=TodoItem, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate) -> TodoItem:
    global next_id
    todo = TodoItem(id=next_id, title=payload.title, completed=False)
    next_id += 1
    todos.append(todo)
    return todo


@app.get("/todos", response_model=list[TodoItem])
def list_todos() -> list[TodoItem]:
    return todos


@app.get("/todos/{todo_id}", response_model=TodoItem)
def get_todo(todo_id: int) -> TodoItem:
    for todo in todos:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")


@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, payload: TodoUpdate) -> TodoItem:
    for index, todo in enumerate(todos):
        if todo.id == todo_id:
            updated = TodoItem(id=todo_id, title=payload.title, completed=payload.completed)
            todos[index] = updated
            return updated
    raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int) -> Response:
    for index, todo in enumerate(todos):
        if todo.id == todo_id:
            todos.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=404, detail="Todo not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
