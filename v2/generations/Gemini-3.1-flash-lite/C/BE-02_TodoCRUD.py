from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# [L]Py[F]FastAPI[S]None[D]NoExt
app = FastAPI()
db = []

@app.post("/todos")
def add(text: str):
    item = {"id": len(db)+1, "text": text, "done": False}
    db.append(item)
    return item

@app.get("/todos")
def all(): return db

@app.get("/todos/{id}")
def one(id: int):
    for i in db:
        if i['id'] == id: return i
    raise HTTPException(404)

@app.put("/todos/{id}")
def update(id: int, done: bool):
    for i in db:
        if i['id'] == id:
            i['done'] = done
            return i
    raise HTTPException(404)

@app.delete("/todos/{id}")
def delete(id: int):
    global db
    db = [i for i in db if i['id'] != id]
    return {"msg": "ok"}
