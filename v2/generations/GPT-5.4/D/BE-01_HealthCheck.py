from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


def current_time_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.get("/health")
async def ping() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "timestamp": current_time_text()})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
