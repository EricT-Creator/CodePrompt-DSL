import csv
import io
from typing import List, Dict, Any, Generator
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator

app = FastAPI()

# In-memory storage for imported records
records_db: List[Dict[str, Any]] = []


class Record(BaseModel):
    """Record model with validation."""
    name: str
    email: EmailStr
    age: int
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    @validator('age')
    def age_must_be_valid(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v


def validate_row(row: Dict[str, str], row_num: int) -> Dict[str, Any]:
    """Validate a single CSV row."""
    errors = []
    
    # Check required fields
    name = row.get('name', '').strip()
    email = row.get('email', '').strip()
    age_str = row.get('age', '').strip()
    
    if not name:
        errors.append("Name is required")
    
    if not email:
        errors.append("Email is required")
    elif '@' not in email or '.' not in email.split('@')[-1]:
        errors.append("Invalid email format")
    
    if not age_str:
        errors.append("Age is required")
    else:
        try:
            age = int(age_str)
            if age < 0 or age > 150:
                errors.append("Age must be between 0 and 150")
        except ValueError:
            errors.append("Age must be a number")
            age = None
    
    if errors:
        return {
            "row": row_num,
            "status": "error",
            "errors": errors,
            "data": row
        }
    
    return {
        "row": row_num,
        "status": "success",
        "data": {
            "name": name,
            "email": email,
            "age": int(age_str)
        }
    }


def process_csv_stream(file_content: str) -> Generator[str, None, None]:
    """Process CSV file and yield results as JSON lines."""
    total = 0
    success = 0
    failed = 0
    
    yield '{"results": ['
    first = True
    
    try:
        reader = csv.DictReader(io.StringIO(file_content))
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            total += 1
            result = validate_row(row, row_num)
            
            if result["status"] == "success":
                success += 1
                records_db.append(result["data"])
            else:
                failed += 1
            
            if not first:
                yield ','
            first = False
            yield f'\n{__import__("json").dumps(result)}'
    
    except csv.Error as e:
        failed += 1
        if not first:
            yield ','
        yield f'\n{{"row": 0, "status": "error", "errors": ["CSV parsing error: {str(e)}"], "data": null}}'
    
    yield f'\n], "summary": {{"total": {total}, "success": {success}, "failed": {failed}}}}}'


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    """
    Import CSV file with name, email, age columns.
    Returns streaming response with line-by-line results.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Return streaming response
    return StreamingResponse(
        process_csv_stream(content_str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="import_result.json"'
        }
    )


@app.get("/data")
async def get_data():
    """Get all imported records."""
    return {
        "count": len(records_db),
        "records": records_db
    }


@app.get("/")
async def root():
    """API documentation."""
    return {
        "endpoints": {
            "POST /import": "Upload CSV file (name, email, age columns)",
            "GET /data": "Get all imported records",
            "GET /docs": "API documentation (Swagger UI)"
        },
        "example_csv": "name,email,age\nJohn Doe,john@example.com,30\nJane Smith,jane@example.com,25"
    }


@app.delete("/data")
async def clear_data():
    """Clear all imported records."""
    global records_db
    count = len(records_db)
    records_db = []
    return {"message": f"Cleared {count} records"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
