import csv
import io
import re
from typing import List, Dict, Any, Generator
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

# In-memory storage
imported_data: List[Dict[str, Any]] = []


class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    skipped: int


def validate_email(email: str) -> bool:
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))


def validate_row(row: Dict[str, str]) -> tuple[bool, str]:
    name = row.get('name', '').strip()
    email = row.get('email', '').strip()
    age_str = row.get('age', '').strip()
    
    if not name:
        return False, "Name is empty"
    
    if not email:
        return False, "Email is empty"
    if not validate_email(email):
        return False, "Invalid email format"
    
    if not age_str:
        return False, "Age is empty"
    try:
        age = int(age_str)
        if age < 0 or age > 150:
            return False, "Age must be between 0 and 150"
    except ValueError:
        return False, "Age must be an integer"
    
    return True, ""


def process_csv(file_content: bytes) -> Generator[str, None, ImportResult]:
    total = 0
    success = 0
    failed = 0
    skipped = 0
    
    try:
        content = file_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = file_content.decode('latin-1')
        except:
            yield json.dumps({"error": "Unable to decode file"}) + "\n"
            return ImportResult(total=0, success=0, failed=0, skipped=0)
    
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        total += 1
        is_valid, error_msg = validate_row(row)
        
        if not is_valid:
            failed += 1
            yield f'{{"row": {total}, "status": "failed", "error": "{error_msg}"}}\n'
            continue
        
        # Check for duplicates
        email = row.get('email', '').strip()
        if any(d.get('email') == email for d in imported_data):
            skipped += 1
            yield f'{{"row": {total}, "status": "skipped", "error": "Duplicate email"}}\n'
            continue
        
        # Store valid record
        record = {
            'name': row.get('name', '').strip(),
            'email': email,
            'age': int(row.get('age', 0))
        }
        imported_data.append(record)
        success += 1
        yield f'{{"row": {total}, "status": "success", "data": {record}}}\n'
    
    # Final summary
    summary = {
        "summary": True,
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped
    }
    yield json.dumps(summary) + "\n"
    
    return ImportResult(total=total, success=success, failed=failed, skipped=skipped)


import json
from typing import AsyncGenerator

async def stream_results(file_content: bytes) -> AsyncGenerator[str, None]:
    total = 0
    success = 0
    failed = 0
    skipped = 0
    
    try:
        content = file_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = file_content.decode('latin-1')
        except:
            yield json.dumps({"error": "Unable to decode file"}) + "\n"
            return
    
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        total += 1
        is_valid, error_msg = validate_row(row)
        
        if not is_valid:
            failed += 1
            yield json.dumps({"row": total, "status": "failed", "error": error_msg}) + "\n"
            continue
        
        email = row.get('email', '').strip()
        if any(d.get('email') == email for d in imported_data):
            skipped += 1
            yield json.dumps({"row": total, "status": "skipped", "error": "Duplicate email"}) + "\n"
            continue
        
        record = {
            'name': row.get('name', '').strip(),
            'email': email,
            'age': int(row.get('age', 0))
        }
        imported_data.append(record)
        success += 1
        yield json.dumps({"row": total, "status": "success", "data": record}) + "\n"
    
    summary = {
        "summary": True,
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped
    }
    yield json.dumps(summary) + "\n"


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    
    return StreamingResponse(
        stream_results(content),
        media_type="application/x-ndjson"
    )


@app.get("/data")
async def get_data():
    return {
        "count": len(imported_data),
        "records": imported_data
    }


@app.delete("/data")
async def clear_data():
    imported_data.clear()
    return {"message": "All data cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
