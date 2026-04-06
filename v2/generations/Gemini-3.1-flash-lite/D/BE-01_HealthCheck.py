from fastapi import FastAPI
from datetime import datetime

# [语]Py[架]FastAPI[式]Mod[依]NoExt[数据]空[出]纯码
app = FastAPI()

@app.get("/health")
def 状态():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
