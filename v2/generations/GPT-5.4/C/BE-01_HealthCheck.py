from datetime import UTC, datetime

from fastapi import APIRouter, FastAPI

router = APIRouter()


@router.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


app = FastAPI()
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
