from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
def read_health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
