import csv
import io
import re
import uuid
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

# In-memory storage
imported_data: List[Dict[str, str | int]] = []


EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_row(row_num: int, row: dict) -> dict:
    """Validate a single row. Returns an error dict or None if valid."""
    errors = []

    name = row.get("name", "").strip()
    if not name:
        errors.append("name: required and must be non-empty")

    email = row.get("email", "").strip()
    if not email:
        errors.append("email: required")
    elif not EMAIL_REGEX.match(email):
        errors.append("email: invalid format (must contain @ and .)")

    age_str = row.get("age", "").strip()
    if not age_str:
        errors.append("age: required")
    else:
        try:
            age = int(age_str)
            if not (0 <= age <= 150):
                errors.append("age: must be an integer between 0 and 150")
        except ValueError:
            errors.append("age: must be a valid integer")

    if errors:
        return {"row": row_num, "status": "failed", "errors": errors}
    return None


def process_csv_stream(content: bytes):
    """Generator that yields processed CSV lines."""
    text = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(text)

    if not reader.fieldnames:
        yield "error: CSV has no headers\n"
        return

    total = 0
    success = 0
    failed = 0
    skipped = 0

    for row_num, row in enumerate(reader, start=2):  # row 1 is header
        total += 1
        error = validate_row(row_num, row)

        if error:
            failed += 1
            error_msg = "; ".join(error["errors"])
            yield f"FAIL,row {error['row']},{error_msg}\n"
        else:
            success += 1
            record = {
                "id": str(uuid.uuid4())[:8],
                "name": row["name"].strip(),
                "email": row["email"].strip(),
                "age": int(row["age"].strip()),
            }
            imported_data.append(record)
            yield f"OK,{record['id']},{record['name']},{record['email']},{record['age']}\n"

    yield f"\nSUMMARY,total={total},success={success},failed={failed},skipped={skipped}\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty CSV file")

    # Validate basic CSV structure
    try:
        text = content.decode("utf-8")
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text[:1024])
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV has no header row")
    except csv.Error:
        raise HTTPException(status_code=400, detail="Invalid CSV format")

    return StreamingResponse(
        process_csv_stream(content),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=import_result.txt"},
    )


@app.get("/data")
async def get_data():
    return {
        "total": len(imported_data),
        "records": imported_data,
    }


@app.get("/")
async def index():
    return {"message": "Batch CSV Import API", "endpoints": ["/import", "/data"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
