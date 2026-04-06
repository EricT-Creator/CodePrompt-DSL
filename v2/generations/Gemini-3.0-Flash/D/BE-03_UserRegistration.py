from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI()

class 用户(BaseModel):
    名: str
    邮: str
    密: str

@app.post("/register", status_code=201)
def 册(人: 用户):
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", 人.邮):
        raise HTTPException(status_code=422, detail="邮格不合")
    if len(人.密) < 8:
        raise HTTPException(status_code=422, detail="密过于简")
    return {"名": 人.名, "邮": 人.邮}
