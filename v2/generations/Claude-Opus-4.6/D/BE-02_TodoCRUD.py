from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

store: list[dict] = []
seq = 0


class NewTodo(BaseModel):
    title: str
    completed: bool = False


class EditTodo(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


@app.post("/todos", status_code=201)
async def create(data: NewTodo):
    global seq
    seq += 1
    record = {"id": seq, "title": data.title, "completed": data.completed}
    store.append(record)
    return record


@app.get("/todos")
async def read_all():
    return store


@app.get("/todos/{item_id}")
async def read_one(item_id: int):
    for r in store:
        if r["id"] == item_id:
            return r
    raise HTTPException(status_code=404, detail="Todo not found")


@app.put("/todos/{item_id}")
async def update(item_id: int, data: EditTodo):
    for r in store:
        if r["id"] == item_id:
            if data.title is not None:
                r["title"] = data.title
            if data.completed is not None:
                r["completed"] = data.completed
            return r
    raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{item_id}")
async def delete(item_id: int):
    for i, r in enumerate(store):
        if r["id"] == item_id:
            store.pop(i)
            return {"detail": "Deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
