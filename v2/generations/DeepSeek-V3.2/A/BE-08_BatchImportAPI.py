import csv
import io
import re
from typing import Dict, List, Generator
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

# Data models
class CSVRow(BaseModel):
    name: str
    email: str
    age: int
    
    @validator('name')
    def name_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    @validator('age')
    def age_range(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v
    
    @validator('email')
    def email_format(cls, v):
        # Simple email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

class ImportResult(BaseModel):
    row_number: int
    status: str  # 'success', 'error', 'skipped'
    data: Optional[Dict]
    error: Optional[str]
    warnings: List[str] = []

class ImportSummary(BaseModel):
    total_rows: int
    successful_rows: int
    failed_rows: int
    skipped_rows: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float

class ImportedRecord(BaseModel):
    id: int
    name: str
    email: str
    age: int
    imported_at: datetime

# Import processor
class CSVImporter:
    def __init__(self):
        self.imported_records: List[ImportedRecord] = []
        self.next_id = 1
        self.import_stats = {
            'total': 0,
            'success': 0,
            'fail': 0,
            'skip': 0
        }
    
    def validate_row(self, row: Dict, row_number: int) -> List[str]:
        """Validate a single row and return list of warnings."""
        warnings = []
        
        # Check for missing fields
        required_fields = ['name', 'email', 'age']
        for field in required_fields:
            if field not in row:
                warnings.append(f"Missing required field: {field}")
        
        # Check name length
        if 'name' in row and len(row['name']) > 100:
            warnings.append("Name exceeds 100 characters")
        
        # Check email length
        if 'email' in row and len(row['email']) > 255:
            warnings.append("Email exceeds 255 characters")
        
        # Try to parse age
        if 'age' in row:
            try:
                age = int(row['age'])
                if age < 0 or age > 150:
                    warnings.append("Age out of range (0-150)")
            except ValueError:
                warnings.append("Age must be a valid integer")
        
        return warnings
    
    def process_row(self, row: Dict, row_number: int) -> ImportResult:
        """Process a single CSV row."""
        self.import_stats['total'] += 1
        
        # Skip empty rows
        if not any(row.values()):
            self.import_stats['skip'] += 1
            return ImportResult(
                row_number=row_number,
                status='skipped',
                data=None,
                error='Empty row',
                warnings=[]
            )
        
        warnings = self.validate_row(row, row_number)
        
        try:
            # Convert age to int if it's a string
            if 'age' in row and isinstance(row['age'], str):
                try:
                    row['age'] = int(row['age'])
                except ValueError:
                    raise ValueError(f"Invalid age value: {row['age']}")
            
            # Validate using Pydantic model
            validated_data = CSVRow(**row)
            
            # Store the record
            record = ImportedRecord(
                id=self.next_id,
                name=validated_data.name,
                email=validated_data.email,
                age=validated_data.age,
                imported_at=datetime.now()
            )
            self.imported_records.append(record)
            self.next_id += 1
            
            self.import_stats['success'] += 1
            
            return ImportResult(
                row_number=row_number,
                status='success',
                data=validated_data.dict(),
                error=None,
                warnings=warnings
            )
            
        except Exception as e:
            self.import_stats['fail'] += 1
            return ImportResult(
                row_number=row_number,
                status='error',
                data=row,
                error=str(e),
                warnings=warnings
            )
    
    def process_csv_stream(self, file_content: bytes) -> Generator[str, None, None]:
        """Process CSV file and yield results as they are processed."""
        start_time = datetime.now()
        
        # Reset stats for new import
        self.import_stats = {'total': 0, 'success': 0, 'fail': 0, 'skip': 0}
        
        # Create string buffer from bytes
        file_text = file_content.decode('utf-8')
        
        # Try to detect delimiter
        sample = file_text[:1024]
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(file_text), delimiter=delimiter)
        
        # Yield header info
        yield f"CSV Import Started at: {start_time.isoformat()}\n"
        yield f"Detected delimiter: '{delimiter}'\n"
        yield f"Columns found: {reader.fieldnames or []}\n"
        yield "-" * 50 + "\n"
        
        # Process rows
        for row_number, row in enumerate(reader, start=1):
            result = self.process_row(row, row_number)
            
            # Yield result as JSON line
            yield result.json() + "\n"
        
        # Calculate summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = ImportSummary(
            total_rows=self.import_stats['total'],
            successful_rows=self.import_stats['success'],
            failed_rows=self.import_stats['fail'],
            skipped_rows=self.import_stats['skip'],
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
        
        yield "-" * 50 + "\n"
        yield "IMPORT SUMMARY:\n"
        yield summary.json(indent=2) + "\n"
    
    def get_all_records(self) -> List[ImportedRecord]:
        """Get all imported records."""
        return self.imported_records
    
    def clear_records(self):
        """Clear all imported records."""
        self.imported_records = []
        self.next_id = 1
        self.import_stats = {'total': 0, 'success': 0, 'fail': 0, 'skip': 0}

# FastAPI app
app = FastAPI(
    title="CSV Batch Import API",
    version="1.0.0",
    description="Batch import CSV files with validation and streaming results"
)

# Create importer instance
importer = CSVImporter()

@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "message": "CSV Batch Import API",
        "endpoints": {
            "POST /import": "Import CSV file with validation",
            "GET /data": "Get all imported records",
            "DELETE /data": "Clear all imported records",
            "GET /stats": "Get import statistics",
            "GET /sample": "Download sample CSV file"
        },
        "current_stats": {
            "total_records": len(importer.imported_records),
            "last_import_stats": importer.import_stats
        }
    }

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    """
    Import a CSV file with validation.
    
    CSV format expected:
    - Columns: name, email, age
    - UTF-8 encoding
    - Comma or semicolon delimiter (auto-detected)
    
    Returns streaming results as each row is processed.
    """
    # Check file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size (limit to 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Create streaming response
        return StreamingResponse(
            importer.process_csv_stream(content),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "X-Filename": file.filename,
                "X-FileSize": str(len(content))
            }
        )
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/data")
async def get_data(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "imported_at",
    sort_order: str = "desc"
):
    """
    Get all imported records with pagination and sorting.
    
    Parameters:
    - limit: Number of records to return (default: 100)
    - offset: Starting offset (default: 0)
    - sort_by: Field to sort by (id, name, email, age, imported_at)
    - sort_order: 'asc' or 'desc' (default: 'desc')
    """
    # Validate parameters
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
    
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be >= 0")
    
    valid_sort_fields = ["id", "name", "email", "age", "imported_at"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {valid_sort_fields}")
    
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="sort_order must be 'asc' or 'desc'")
    
    # Get all records
    all_records = importer.get_all_records()
    
    # Sort records
    reverse = sort_order == "desc"
    
    if sort_by == "id":
        all_records.sort(key=lambda x: x.id, reverse=reverse)
    elif sort_by == "name":
        all_records.sort(key=lambda x: x.name.lower(), reverse=reverse)
    elif sort_by == "email":
        all_records.sort(key=lambda x: x.email.lower(), reverse=reverse)
    elif sort_by == "age":
        all_records.sort(key=lambda x: x.age, reverse=reverse)
    elif sort_by == "imported_at":
        all_records.sort(key=lambda x: x.imported_at, reverse=reverse)
    
    # Apply pagination
    total_records = len(all_records)
    paginated_records = all_records[offset:offset + limit]
    
    return {
        "total_records": total_records,
        "returned_records": len(paginated_records),
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "has_more": offset + limit < total_records,
        "next_offset": offset + limit if offset + limit < total_records else None,
        "records": [record.dict() for record in paginated_records]
    }

@app.delete("/data")
async def clear_data():
    """Clear all imported records."""
    old_count = len(importer.imported_records)
    importer.clear_records()
    
    return {
        "message": "All imported records cleared",
        "cleared_records": old_count,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Get import statistics."""
    all_records = importer.get_all_records()
    
    if not all_records:
        return {
            "message": "No records imported yet",
            "total_records": 0,
            "import_stats": importer.import_stats
        }
    
    # Calculate statistics
    ages = [record.age for record in all_records]
    email_domains = [record.email.split('@')[1] for record in all_records if '@' in record.email]
    
    # Count by domain
    domain_counts = {}
    for domain in email_domains:
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    # Most common domain
    most_common_domain = max(domain_counts.items(), key=lambda x: x[1]) if domain_counts else ("N/A", 0)
    
    return {
        "total_records": len(all_records),
        "import_stats": importer.import_stats,
        "age_statistics": {
            "min": min(ages) if ages else 0,
            "max": max(ages) if ages else 0,
            "average": sum(ages) / len(ages) if ages else 0,
            "median": sorted(ages)[len(ages) // 2] if ages else 0
        },
        "email_statistics": {
            "total_domains": len(domain_counts),
            "most_common_domain": most_common_domain[0],
            "most_common_count": most_common_domain[1],
            "domain_distribution": domain_counts
        },
        "time_range": {
            "oldest_record": min(record.imported_at for record in all_records).isoformat() if all_records else "N/A",
            "newest_record": max(record.imported_at for record in all_records).isoformat() if all_records else "N/A"
        }
    }

@app.get("/sample")
async def download_sample():
    """Download a sample CSV file with correct format."""
    sample_data = """name,email,age
John Doe,john@example.com,30
Jane Smith,jane@example.com,25
Bob Johnson,bob@example.com,45
Alice Brown,alice@example.com,35
Charlie Wilson,charlie@example.com,28
Diana Lee,diana@example.com,32
Edward Taylor,edward@example.com,40
Fiona Clark,fiona@example.com,29
George Lewis,george@example.com,50
Helen Walker,helen@example.com,27"""
    
    return StreamingResponse(
        io.StringIO(sample_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=sample_data.csv",
            "X-Sample-Rows": "10"
        }
    )

@app.get("/search")
async def search_records(
    name: str = None,
    email: str = None,
    min_age: int = None,
    max_age: int = None,
    limit: int = 50
):
    """Search imported records by various criteria."""
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 200")
    
    all_records = importer.get_all_records()
    results = []
    
    for record in all_records:
        match = True
        
        # Filter by name (case-insensitive partial match)
        if name and name.lower() not in record.name.lower():
            match = False
        
        # Filter by email (case-insensitive partial match)
        if email and email.lower() not in record.email.lower():
            match = False
        
        # Filter by age range
        if min_age is not None and record.age < min_age:
            match = False
        
        if max_age is not None and record.age > max_age:
            match = False
        
        if match:
            results.append(record)
        
        if len(results) >= limit:
            break
    
    return {
        "search_criteria": {
            "name": name,
            "email": email,
            "min_age": min_age,
            "max_age": max_age
        },
        "total_matches": len(results),
        "limit": limit,
        "records": [record.dict() for record in results]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)