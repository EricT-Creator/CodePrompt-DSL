import csv
import io
import re
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

app = FastAPI(title="Batch Import API")

stored_rows: list[dict[str, Any]] = []
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
REQUIRED_HEADERS = ["name", "email", "age"]


def validate_row(row_number: int, row: dict[str, str]) -> tuple[bool, str, dict[str, Any] | None]:
    normalized = {key.strip().lower(): (value or '').strip() for key, value in row.items()}
    name = normalized.get("name", "")
    email = normalized.get("email", "")
    age_text = normalized.get("age", "")

    if not name:
      return False, f"row {row_number}: name is required", None
    if not EMAIL_PATTERN.fullmatch(email):
      return False, f"row {row_number}: invalid email '{email}'", None
    try:
      age = int(age_text)
    except ValueError:
      return False, f"row {row_number}: age must be an integer", None
    if age < 0 or age > 150:
      return False, f"row {row_number}: age must be between 0 and 150", None

    clean = {"name": name, "email": email, "age": age}
    return True, f"row {row_number}: imported {email}", clean


async def stream_import(file: UploadFile):
    total = 0
    success = 0
    failed = 0

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail=f"Unable to decode CSV as UTF-8: {error}")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV header row is missing")

    normalized_headers = [header.strip().lower() for header in reader.fieldnames]
    if normalized_headers != REQUIRED_HEADERS:
        raise HTTPException(status_code=400, detail=f"Headers must be exactly {REQUIRED_HEADERS}")

    yield "status: import started\n"
    for total, row in enumerate(reader, start=1):
        ok, message, clean = validate_row(total, row)
        if ok and clean is not None:
            success += 1
            stored_rows.append(clean)
            yield f"success: {message}\n"
        else:
            failed += 1
            yield f"failed: {message}\n"

    yield f"summary: total={total}, success={success}, failed={failed}\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    return StreamingResponse(stream_import(file), media_type="text/plain; charset=utf-8")


@app.get("/data")
async def get_data():
    return {"total": len(stored_rows), "items": stored_rows}


@app.get("/")
async def root():
    return {"service": "batch-import-api", "required_headers": REQUIRED_HEADERS}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
