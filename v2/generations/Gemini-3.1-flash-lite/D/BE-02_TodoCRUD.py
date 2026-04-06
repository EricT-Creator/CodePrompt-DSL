from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# [语]Py[架]FastAPI[式]Mod[依]NoExt[数据]Mock[出]纯码
app = FastAPI()
db = []

class 待办(BaseModel):
    id: int
    内容: str
    毕: bool = False

@app.post("/todos")
def 增(内容: str):
    项 = 待办(id=len(db)+1, 内容=内容)
    db.append(项)
    return 项

@app.get("/todos")
def 取全(): return db

@app.get("/todos/{id}")
def 取一(id: int):
    for i in db:
        if i.id == id: return i
    raise HTTPException(404)

@app.put("/todos/{id}")
def 改(id: int, 毕: bool):
    for i in db:
        if i.id == id:
            i.毕 = 毕
            return i
    raise HTTPException(404)

@app.delete("/todos/{id}")
def 删(id: int):
    global db
    db = [i for i in db if i.id != id]
    return {"msg": "ok"}
