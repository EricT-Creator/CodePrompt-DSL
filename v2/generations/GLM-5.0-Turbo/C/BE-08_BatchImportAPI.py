import csv
import io
import re
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="CSV Batch Import API")

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Storage
imported_data: List[Dict] = []
import_summary: Dict = {"total": 0, "success": 0, "failed": 0}


def validate_row(row_num: int, row: Dict[str, str]) -> Dict:
    errors = []
    name = row.get("name", "").strip()
    email = row.get("email", "").strip()
    age_str = row.get("age", "").strip()

    if not name:
        errors.append("name is required and cannot be empty")
    if not email:
        errors.append("email is required")
    elif not EMAIL_REGEX.match(email):
        errors.append(f"invalid email format: '{email}'")
    if not age_str:
        errors.append("age is required")
    else:
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                errors.append(f"age must be between 0 and 150, got {age}")
        except ValueError:
            errors.append(f"age must be a number, got '{age_str}'")

    return {"row": row_num, "name": name, "email": email, "age": age_str, "errors": errors, "valid": len(errors) == 0}


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    global imported_data, import_summary
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    text_content = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_content))

    if not reader.fieldnames or "name" not in reader.fieldnames or "email" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must have 'name' and 'email' columns")

    results = []
    total = 0
    success = 0
    failed = 0

    for row_num, row in enumerate(reader, start=2):
        total += 1
        validation = validate_row(row_num, row)
        results.append(validation)
        if validation["valid"]:
            success += 1
            imported_data.append({
                "name": validation["name"],
                "email": validation["email"],
                "age": int(validation["age"]),
            })
        else:
            failed += 1

    import_summary = {"total": total, "success": success, "failed": failed}

    def generate_log():
        yield "row,status,name,email,age,errors\n"
        for r in results:
            status = "success" if r["valid"] else "failed"
            error_str = "; ".join(r["errors"])
            yield f'{r["row"]},{status},"{r["name"]}","{r["email"]}","{r["age"]}","{error_str}"\n'

    response = StreamingResponse(
        generate_log(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_log.csv"},
    )
    return response


@app.get("/data")
def get_data():
    return {"count": len(imported_data), "data": imported_data}


@app.get("/summary")
def get_summary():
    return import_summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
