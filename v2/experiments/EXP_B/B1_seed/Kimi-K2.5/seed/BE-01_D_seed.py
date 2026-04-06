from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
