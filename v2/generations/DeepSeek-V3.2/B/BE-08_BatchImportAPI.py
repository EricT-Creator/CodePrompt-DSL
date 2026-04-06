import csv
import io
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Generator

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator, EmailStr

app = FastAPI(title="CSV Batch Import API")

# Data models
class ImportRecord(BaseModel):
    """Validated import record"""
    name: str
    email: EmailStr
    age: int
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 100:
            raise ValueError('Name too long')
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v

class ImportResult(BaseModel):
    """Result for a single CSV row"""
    line_number: int
    data: Dict[str, Any]
    success: bool
    errors: List[str] = []
    processed_at: str

class ImportSummary(BaseModel):
    """Summary of batch import"""
    total_rows: int
    successful: int
    failed: int
    processing_time_ms: float
    start_time: str
    end_time: str

class StoredRecord(BaseModel):
    """Record stored in memory"""
    id: int
    name: str
    email: str
    age: int
    imported_at: str

# In-memory storage
records_store: List[StoredRecord] = []
next_id = 1

# Validation functions
def validate_email(email: str) -> bool:
    """Validate email format"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, email))

def validate_row(row: Dict, line_number: int) -> tuple[bool, List[str], Optional[Dict]]:
    """
    Validate a single CSV row.
    
    Returns:
        (is_valid, errors, validated_data)
    """
    errors = []
    
    # Check required fields
    required_fields = ['name', 'email', 'age']
    for field in required_fields:
        if field not in row:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors, None
    
    # Validate name
    name = str(row['name']).strip()
    if len(name) < 2:
        errors.append("Name must be at least 2 characters long")
    
    # Validate email
    email = str(row['email']).strip().lower()
    if not validate_email(email):
        errors.append("Invalid email format")
    
    # Validate age
    try:
        age = int(row['age'])
        if age < 0 or age > 150:
            errors.append("Age must be between 0 and 150")
    except (ValueError, TypeError):
        errors.append("Age must be a valid integer")
        age = None
    
    if errors:
        return False, errors, None
    
    return True, [], {
        'name': name,
        'email': email,
        'age': age,
    }

# CSV parsing and processing
def process_csv_stream(file_content: bytes) -> Generator[Dict, None, None]:
    """
    Parse CSV content and yield rows with validation.
    """
    # Decode file content
    content = file_content.decode('utf-8')
    
    # Create CSV reader
    csv_file = io.StringIO(content)
    reader = csv.DictReader(csv_file)
    
    # Check headers
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty CSV file")
    
    expected_headers = {'name', 'email', 'age'}
    missing_headers = expected_headers - set(reader.fieldnames)
    if missing_headers:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required CSV columns: {missing_headers}"
        )
    
    # Process rows
    for line_number, row in enumerate(reader, start=2):  # Line 1 is header
        yield {
            'line_number': line_number,
            'raw_row': row,
        }

def generate_results_stream(results: List[ImportResult]) -> Generator[str, None, None]:
    """
    Generate streaming JSON response with results.
    """
    yield '[\n'
    
    for i, result in enumerate(results):
        result_json = json.dumps(result.dict())
        if i < len(results) - 1:
            yield result_json + ',\n'
        else:
            yield result_json
    
    yield '\n]'

# Routes
@app.post("/import", response_model=ImportSummary)
async def import_csv(file: UploadFile = File(...)):
    """
    Import CSV file with batch processing.
    
    Returns streaming response with line-by-line results.
    """
    global next_id
    
    start_time = datetime.now()
    
    # Check file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Process CSV
    results: List[ImportResult] = []
    successful_records: List[Dict] = []
    
    try:
        for item in process_csv_stream(file_content):
            line_number = item['line_number']
            raw_row = item['raw_row']
            
            # Validate row
            is_valid, errors, validated_data = validate_row(raw_row, line_number)
            
            if is_valid:
                # Store record
                record = StoredRecord(
                    id=next_id,
                    name=validated_data['name'],
                    email=validated_data['email'],
                    age=validated_data['age'],
                    imported_at=datetime.now().isoformat(),
                )
                records_store.append(record)
                successful_records.append(validated_data)
                next_id += 1
            
            # Create result
            result = ImportResult(
                line_number=line_number,
                data=raw_row,
                success=is_valid,
                errors=errors,
                processed_at=datetime.now().isoformat(),
            )
            results.append(result)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV processing error: {str(e)}")
    
    end_time = datetime.now()
    processing_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Create summary
    summary = ImportSummary(
        total_rows=len(results),
        successful=len(successful_records),
        failed=len(results) - len(successful_records),
        processing_time_ms=processing_time_ms,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
    )
    
    # Return streaming response
    def result_generator():
        yield '{"summary": '
        yield json.dumps(summary.dict())
        yield ', "results": '
        
        for chunk in generate_results_stream(results):
            yield chunk
        
        yield '}'
    
    return StreamingResponse(
        result_generator(),
        media_type="application/json",
        headers={
            "X-Total-Rows": str(len(results)),
            "X-Successful": str(len(successful_records)),
            "X-Failed": str(len(results) - len(successful_records)),
        }
    )

@app.get("/data")
async def get_all_data(
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "id",
    sort_order: str = "asc"
):
    """
    Get all imported records with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        sort_by: Field to sort by (id, name, email, age, imported_at)
        sort_order: Sort order (asc or desc)
    """
    # Validate sort parameters
    valid_sort_fields = {'id', 'name', 'email', 'age', 'imported_at'}
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Must be one of: {valid_sort_fields}"
        )
    
    if sort_order not in {'asc', 'desc'}:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort order. Must be 'asc' or 'desc'"
        )
    
    # Create a copy for sorting
    sorted_records = records_store.copy()
    
    # Sort records
    reverse = sort_order == 'desc'
    
    if sort_by == 'id':
        sorted_records.sort(key=lambda x: x.id, reverse=reverse)
    elif sort_by == 'name':
        sorted_records.sort(key=lambda x: x.name.lower(), reverse=reverse)
    elif sort_by == 'email':
        sorted_records.sort(key=lambda x: x.email.lower(), reverse=reverse)
    elif sort_by == 'age':
        sorted_records.sort(key=lambda x: x.age, reverse=reverse)
    elif sort_by == 'imported_at':
        sorted_records.sort(key=lambda x: x.imported_at, reverse=reverse)
    
    # Apply pagination
    paginated_records = sorted_records[skip:skip + limit]
    
    return {
        "total": len(records_store),
        "skip": skip,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "data": paginated_records,
    }

@app.get("/data/{record_id}")
async def get_record(record_id: int):
    """Get a specific record by ID"""
    for record in records_store:
        if record.id == record_id:
            return record
    
    raise HTTPException(status_code=404, detail="Record not found")

@app.delete("/data/{record_id}")
async def delete_record(record_id: int):
    """Delete a specific record by ID"""
    global records_store
    
    original_length = len(records_store)
    records_store = [r for r in records_store if r.id != record_id]
    
    if len(records_store) == original_length:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {"message": f"Record {record_id} deleted", "remaining": len(records_store)}

@app.get("/stats")
async def get_statistics():
    """Get import statistics"""
    if not records_store:
        return {
            "total_records": 0,
            "age_stats": None,
            "import_timeline": [],
        }
    
    # Age statistics
    ages = [r.age for r in records_store]
    
    # Import timeline (by day)
    timeline = {}
    for record in records_store:
        date = record.imported_at[:10]  # YYYY-MM-DD
        timeline[date] = timeline.get(date, 0) + 1
    
    return {
        "total_records": len(records_store),
        "age_stats": {
            "average": sum(ages) / len(ages),
            "min": min(ages),
            "max": max(ages),
        },
        "import_timeline": [
            {"date": date, "count": count}
            for date, count in sorted(timeline.items())
        ],
    }

@app.get("/export")
async def export_data():
    """Export all records as CSV"""
    if not records_store:
        raise HTTPException(status_code=404, detail="No records to export")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['id', 'name', 'email', 'age', 'imported_at'])
    writer.writeheader()
    
    for record in records_store:
        writer.writerow(record.dict())
    
    # Return as downloadable CSV
    csv_content = output.getvalue()
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=exported_records.csv",
            "X-Total-Records": str(len(records_store)),
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)