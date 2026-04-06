from datetime import datetime
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
