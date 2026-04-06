from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
库 = []

class 待办(BaseModel):
    号: int
    事: str

@app.post("/todos")
def 增(项: 待办):
    库.append(项)
    return 项

@app.get("/todos")
def 览():
    return 库

@app.get("/todos/{id}")
def 查(id: int):
    for i in 库:
        if i.号 == id: return i
    raise HTTPException(404)

@app.put("/todos/{id}")
def 改(id: int, 项: 待办):
    for 序, i in enumerate(库):
        if i.号 == id:
            库[序] = 项
            return 项
    raise HTTPException(404)

@app.delete("/todos/{id}")
def 删(id: int):
    global 库
    库 = [i for i in 库 if i.号 != id]
    return {"状": "毕"}
