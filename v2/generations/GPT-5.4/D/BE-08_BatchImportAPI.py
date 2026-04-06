import csv
import io
import json
import re
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

app = FastAPI(title="CSV Batch Import API")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
REQUIRED_FIELDS = ["name", "email", "age"]
records: list[dict[str, Any]] = []


def validate_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []

    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    age_text = row.get("age", "").strip()

    if not name:
        errors.append("name must not be empty")

    if not email:
        errors.append("email must not be empty")
    elif not EMAIL_PATTERN.fullmatch(email):
        errors.append("email format is invalid")

    if not age_text:
        errors.append("age must not be empty")
    else:
        try:
            age = int(age_text)
            if age < 0 or age > 150:
                errors.append("age must be between 0 and 150")
        except ValueError:
            errors.append("age must be an integer")

    return errors


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    try:
        raw_content = await file.read()
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV must include a header row")

    normalized_headers = [field.strip() for field in reader.fieldnames]
    if normalized_headers != REQUIRED_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV headers must be exactly: {', '.join(REQUIRED_FIELDS)}",
        )

    def stream_rows():
        total = 0
        success = 0
        failed = 0

        for line_number, raw_row in enumerate(reader, start=2):
            total += 1
            row = {key.strip(): (value or "").strip() for key, value in raw_row.items() if key is not None}
            errors = validate_row(row)

            if errors:
                failed += 1
                yield json.dumps(
                    {
                        "line": line_number,
                        "status": "failed",
                        "errors": errors,
                        "row": row,
                    },
                    ensure_ascii=False,
                ) + "\n"
                continue

            record = {
                "name": row["name"],
                "email": row["email"],
                "age": int(row["age"]),
            }
            records.append(record)
            success += 1
            yield json.dumps(
                {
                    "line": line_number,
                    "status": "success",
                    "record": record,
                },
                ensure_ascii=False,
            ) + "\n"

        yield json.dumps(
            {
                "summary": {
                    "total": total,
                    "success": success,
                    "failed": failed,
                }
            },
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(stream_rows(), media_type="application/x-ndjson")


@app.get("/data")
async def get_data():
    return {
        "count": len(records),
        "items": records,
    }


@app.get("/")
async def index():
    return {
        "message": "Upload a CSV file to POST /import with headers name,email,age.",
        "records": len(records),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
