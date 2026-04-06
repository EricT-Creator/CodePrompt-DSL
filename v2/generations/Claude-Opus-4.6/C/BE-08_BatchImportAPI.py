import csv
import io
import re
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI()

data_store: List[Dict[str, str]] = []


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_row(row: dict, row_num: int) -> tuple:
    errors = []
    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    age_str = row.get("age", "").strip()

    if not name:
        errors.append(f"Row {row_num}: name is empty")

    if not email:
        errors.append(f"Row {row_num}: email is empty")
    elif not validate_email(email):
        errors.append(f"Row {row_num}: invalid email format '{email}'")

    age = None
    if not age_str:
        errors.append(f"Row {row_num}: age is empty")
    else:
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                errors.append(f"Row {row_num}: age {age} out of range (0-150)")
        except ValueError:
            errors.append(f"Row {row_num}: age '{age_str}' is not a valid integer")

    return errors, {"name": name, "email": email, "age": age_str}


async def process_csv_stream(content: str):
    reader = csv.DictReader(io.StringIO(content))

    required_fields = {"name", "email", "age"}
    if reader.fieldnames is None:
        yield "ERROR: CSV has no headers\n"
        return

    headers = set(f.strip().lower() for f in reader.fieldnames)
    missing = required_fields - headers
    if missing:
        yield f"ERROR: Missing required columns: {', '.join(missing)}\n"
        return

    total = 0
    success = 0
    failed = 0

    yield "--- Processing CSV ---\n"

    for i, raw_row in enumerate(reader, start=2):
        row = {k.strip().lower(): v.strip() if v else "" for k, v in raw_row.items()}
        total += 1
        errors, cleaned = validate_row(row, i)

        if errors:
            failed += 1
            for err in errors:
                yield f"FAIL: {err}\n"
        else:
            success += 1
            data_store.append(cleaned)
            yield f"OK: Row {i} - {cleaned['name']} ({cleaned['email']}, age {cleaned['age']})\n"

    yield "--- Summary ---\n"
    yield f"Total: {total}\n"
    yield f"Success: {success}\n"
    yield f"Failed: {failed}\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        return JSONResponse(
            status_code=400,
            content={"detail": "Only .csv files are accepted"},
        )

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    return StreamingResponse(
        process_csv_stream(text),
        media_type="text/plain",
        headers={"X-Content-Type": "text/plain; charset=utf-8"},
    )


@app.get("/data")
async def get_data():
    return {
        "count": len(data_store),
        "records": data_store,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
