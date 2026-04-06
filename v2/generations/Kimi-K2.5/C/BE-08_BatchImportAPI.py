import csv
import io
import re
from typing import List, Dict, Generator, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="CSV Batch Import API")

class ImportSummary(BaseModel):
    total: int
    success: int
    failed: int

class DataRecord(BaseModel):
    name: str
    email: str
    age: int

class ValidationError(BaseModel):
    row: int
    errors: List[str]

stored_data: List[Dict] = []

def validate_name(name: str) -> Tuple[bool, str]:
    if not name or not name.strip():
        return False, "Name cannot be empty"
    return True, ""

def validate_email(email: str) -> Tuple[bool, str]:
    if not email or not email.strip():
        return False, "Email cannot be empty"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""

def validate_age(age_str: str) -> Tuple[bool, str, int]:
    if not age_str or not age_str.strip():
        return False, "Age cannot be empty", 0
    try:
        age = int(age_str)
        if age < 0 or age > 150:
            return False, "Age must be between 0 and 150", 0
        return True, "", age
    except ValueError:
        return False, "Age must be a valid number", 0

def validate_row(row: Dict, row_num: int) -> Tuple[bool, List[str], Dict]:
    errors = []
    record = {}
    
    name = row.get('name', '')
    valid, error = validate_name(name)
    if not valid:
        errors.append(error)
    else:
        record['name'] = name.strip()
    
    email = row.get('email', '')
    valid, error = validate_email(email)
    if not valid:
        errors.append(error)
    else:
        record['email'] = email.strip()
    
    age_str = row.get('age', '')
    valid, error, age = validate_age(age_str)
    if not valid:
        errors.append(error)
    else:
        record['age'] = age
    
    return len(errors) == 0, errors, record

def process_csv_stream(file_content: bytes) -> Generator[str, None, ImportSummary]:
    total = 0
    success = 0
    failed = 0
    
    yield '{"status": "processing", "message": "Starting import..."}\n'
    
    try:
        content_str = file_content.decode('utf-8')
    except UnicodeDecodeError:
        content_str = file_content.decode('latin-1')
    
    csv_file = io.StringIO(content_str)
    reader = csv.DictReader(csv_file)
    
    for row_num, row in enumerate(reader, start=2):
        total += 1
        valid, errors, record = validate_row(row, row_num)
        
        if valid:
            stored_data.append(record)
            success += 1
            yield f'{{"row": {row_num}, "status": "success", "data": {record}}}\n'
        else:
            failed += 1
            yield f'{{"row": {row_num}, "status": "failed", "errors": {errors}}}\n'
    
    summary = ImportSummary(total=total, success=success, failed=failed)
    yield f'{{"status": "complete", "summary": {summary.model_dump()}}}\n'

@app.get("/")
async def root():
    return {
        "message": "CSV Batch Import API",
        "endpoints": ["/import (POST)", "/data (GET)"],
        "validation_rules": {
            "name": "Non-empty string",
            "email": "Valid email format",
            "age": "Integer between 0 and 150"
        }
    }

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    
    def event_generator():
        for line in process_csv_stream(content):
            yield line
    
    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )

@app.get("/data")
async def get_data(skip: int = 0, limit: int = 100):
    return {
        "total": len(stored_data),
        "skip": skip,
        "limit": limit,
        "data": stored_data[skip:skip + limit]
    }

@app.delete("/data")
async def clear_data():
    stored_data.clear()
    return {"message": "All data cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
