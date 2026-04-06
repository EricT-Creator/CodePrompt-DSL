from fastapi import FastAPI
from datetime import datetime

# [L]Py[F]FastAPI[S]None[D]NoExt
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": str(datetime.now())}
