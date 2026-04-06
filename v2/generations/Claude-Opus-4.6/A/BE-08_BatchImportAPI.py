import csv
import io
import re
import time
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse

app = FastAPI()

imported_records: List[Dict[str, Any]] = []


def validate_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def validate_age(age_str: str) -> tuple[bool, int]:
    try:
        age = int(age_str.strip())
        return 0 <= age <= 150, age
    except (ValueError, TypeError):
        return False, 0


def validate_row(row: dict) -> tuple[bool, str, dict]:
    errors = []
    name = row.get('name', '').strip()
    email = row.get('email', '').strip()
    age_str = row.get('age', '').strip()

    if not name:
        errors.append('name is empty')
    if not email:
        errors.append('email is empty')
    elif not validate_email(email):
        errors.append(f'invalid email format: {email}')

    if not age_str:
        errors.append('age is empty')
    else:
        age_valid, age_val = validate_age(age_str)
        if not age_valid:
            errors.append(f'invalid age: {age_str} (must be integer 0-150)')

    if errors:
        return False, '; '.join(errors), {}

    _, age_val = validate_age(age_str)
    return True, '', {'name': name, 'email': email, 'age': age_val}


async def process_csv_stream(file_content: str):
    reader = csv.DictReader(io.StringIO(file_content))

    required_fields = {'name', 'email', 'age'}
    if reader.fieldnames is None:
        yield f"ERROR: CSV file has no headers\n"
        return

    headers = set(f.strip().lower() for f in reader.fieldnames)
    missing = required_fields - headers
    if missing:
        yield f"ERROR: Missing required columns: {', '.join(missing)}\n"
        return

    total = 0
    success = 0
    failed = 0
    skipped = 0

    yield f"Processing CSV file...\n"

    for i, raw_row in enumerate(reader, start=1):
        row = {k.strip().lower(): v.strip() if v else '' for k, v in raw_row.items()}
        total += 1

        if not any(row.values()):
            skipped += 1
            yield f"Row {i}: SKIPPED (empty row)\n"
            continue

        is_valid, error_msg, clean_data = validate_row(row)

        if is_valid:
            imported_records.append(clean_data)
            success += 1
            yield f"Row {i}: OK - {clean_data['name']} ({clean_data['email']}, age {clean_data['age']})\n"
        else:
            failed += 1
            yield f"Row {i}: FAILED - {error_msg}\n"

    yield f"\n--- Summary ---\n"
    yield f"Total rows: {total}\n"
    yield f"Success: {success}\n"
    yield f"Failed: {failed}\n"
    yield f"Skipped: {skipped}\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith('.csv'):
        return StreamingResponse(
            iter(["ERROR: Please upload a .csv file\n"]),
            media_type="text/plain",
        )

    content = await file.read()
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            file_content = content.decode('latin-1')
        except Exception:
            return StreamingResponse(
                iter(["ERROR: Unable to decode file\n"]),
                media_type="text/plain",
            )

    return StreamingResponse(
        process_csv_stream(file_content),
        media_type="text/plain",
    )


@app.get("/data")
async def get_data():
    return {
        "total_records": len(imported_records),
        "records": imported_records,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
