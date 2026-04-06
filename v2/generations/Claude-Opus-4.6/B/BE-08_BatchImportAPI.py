import csv
import io
import re
from typing import Dict, List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="CSV Batch Import API")

records_db: List[Dict[str, str]] = []


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def validate_age(age_str: str) -> bool:
    try:
        age = int(age_str.strip())
        return 0 < age < 150
    except (ValueError, TypeError):
        return False


def validate_row(row: Dict[str, str], row_num: int) -> List[str]:
    errors = []
    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    age = row.get("age", "").strip()

    if not name:
        errors.append(f"Row {row_num}: name is empty")
    if not email:
        errors.append(f"Row {row_num}: email is empty")
    elif not validate_email(email):
        errors.append(f"Row {row_num}: invalid email '{email}'")
    if not age:
        errors.append(f"Row {row_num}: age is empty")
    elif not validate_age(age):
        errors.append(f"Row {row_num}: invalid age '{age}'")

    return errors


async def process_csv_stream(content: str):
    reader = csv.DictReader(io.StringIO(content))

    required_fields = {"name", "email", "age"}
    if reader.fieldnames is None:
        yield "ERROR: CSV file has no header row\n"
        return

    header_set = {f.strip().lower() for f in reader.fieldnames}
    missing = required_fields - header_set
    if missing:
        yield f"ERROR: Missing required columns: {', '.join(missing)}\n"
        return

    total = 0
    success_count = 0
    error_count = 0
    error_details: List[str] = []

    for row_num, raw_row in enumerate(reader, start=2):
        total += 1
        row = {k.strip().lower(): v.strip() if v else "" for k, v in raw_row.items()}
        errors = validate_row(row, row_num)

        if errors:
            error_count += 1
            for err in errors:
                error_details.append(err)
                yield f"FAIL | {err}\n"
        else:
            record = {
                "name": row["name"],
                "email": row["email"],
                "age": row["age"],
            }
            records_db.append(record)
            success_count += 1
            yield f"OK   | Row {row_num}: {record['name']} <{record['email']}> age={record['age']}\n"

    yield "\n--- SUMMARY ---\n"
    yield f"Total rows processed: {total}\n"
    yield f"Successful imports:   {success_count}\n"
    yield f"Failed rows:          {error_count}\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    raw_bytes = await file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode file")

    async def generate():
        async for line in process_csv_stream(content):
            yield line

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/data")
async def get_all_data():
    return {
        "total_records": len(records_db),
        "records": records_db,
    }


@app.delete("/data")
async def clear_data():
    count = len(records_db)
    records_db.clear()
    return {"message": f"Cleared {count} records"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
