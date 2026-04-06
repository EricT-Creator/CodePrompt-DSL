from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class 算(BaseModel):
    甲: float
    乙: float
    法: str

@app.post("/calculate")
def calculate(s: 算):
    if s.法 == 'add': return {"值": s.甲 + s.乙}
    if s.法 == 'sub': return {"值": s.甲 - s.乙}
    if s.法 == 'mul': return {"值": s.甲 * s.乙}
    if s.法 == 'div':
        if s.乙 == 0: raise HTTPException(400)
        return {"值": s.甲 / s.乙}
    raise HTTPException(400)
