import csv
import io
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()

# In-memory storage
records: List[dict] = []
import_lock = False


class RecordSummary(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[dict]


def validate_row(row_num: int, row: dict) -> tuple[bool, str]:
    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    age_str = row.get("age", "").strip()

    if not name:
        return False, f"Row {row_num}: name is required"
    if len(name) > 100:
        return False, f"Row {row_num}: name exceeds 100 characters"

    if not email:
        return False, f"Row {row_num}: email is required"
    if not all(c in email for c in ["@", "."]):
        return False, f"Row {row_num}: invalid email format"
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
        return False, f"Row {row_num}: invalid email format"

    if not age_str:
        return False, f"Row {row_num}: age is required"
    try:
        age = int(age_str)
        if age < 0 or age > 150:
            return False, f"Row {row_num}: age must be between 0 and 150"
    except ValueError:
        return False, f"Row {row_num}: age must be a valid integer"

    return True, ""


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    global import_lock
    if import_lock:
        raise HTTPException(status_code=409, detail="An import is already in progress")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode file")

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    required_fields = {"name", "email", "age"}
    if not required_fields.issubset(set(reader.fieldnames)):
        missing = required_fields - set(reader.fieldnames)
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}"
        )

    async def generate_results():
        nonlocal import_lock
        import_lock = True
        total = 0
        success = 0
        failed = 0
        errors = []

        yield "row,status,name,email,age,error\n"

        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            total += 1
            valid, error_msg = validate_row(row_num, row)

            if valid:
                success += 1
                record = {
                    "name": row["name"].strip(),
                    "email": row["email"].strip(),
                    "age": int(row["age"].strip()),
                }
                records.append(record)
                yield csv_line([str(row_num), "success", record["name"], record["email"], str(record["age"]), ""])
            else:
                failed += 1
                err = {"row": row_num, "error": error_msg}
                errors.append(err)
                yield csv_line([str(row_num), "failed", row.get("name", ""), row.get("email", ""), row.get("age", ""), error_msg])

        import_lock = False

    def csv_line(fields: list) -> str:
        return ",".join(f'"{f}"' if "," in f or '"' in f else f for f in fields) + "\n"

    return StreamingResponse(
        generate_results(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="import_results.csv"'
        },
    )


@app.get("/data")
async def get_data():
    return {
        "total": len(records),
        "records": records,
    }


@app.get("/import/status")
async def import_status():
    return {
        "in_progress": import_lock,
        "total_records": len(records),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
