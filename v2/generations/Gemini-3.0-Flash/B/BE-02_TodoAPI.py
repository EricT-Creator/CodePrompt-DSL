from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Item(BaseModel):
    id: int
    title: str
    done: bool = False

db: List[Item] = []

@app.post("/todos", status_code=201)
def create(item: Item):
    db.append(item)
    return item

@app.get("/todos")
def list_all():
    return db

@app.get("/todos/{id}")
def get_one(id: int):
    for i in db:
        if i.id == id: return i
    raise HTTPException(404)

@app.put("/todos/{id}")
def update(id: int, item: Item):
    for idx, i in enumerate(db):
        if i.id == id:
            db[idx] = item
            return item
    raise HTTPException(404)

@app.delete("/todos/{id}", status_code=204)
def delete(id: int):
    global db
    db = [i for i in db if i.id != id]
    return
