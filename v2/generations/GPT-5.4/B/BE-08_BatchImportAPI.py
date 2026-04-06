import csv
import io
import json
import re
from typing import Dict, Generator, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="CSV Batch Import API")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
EXPECTED_HEADER = ["name", "email", "age"]


class Record(BaseModel):
    id: int
    name: str
    email: str
    age: int


stored_records: List[Record] = []


def validate_row(row: List[str]) -> Dict[str, object]:
    if len(row) != 3:
        return {"valid": False, "error": "Each row must contain exactly 3 columns: name,email,age"}

    name = row[0].strip()
    email = row[1].strip()
    age_raw = row[2].strip()

    if not name:
        return {"valid": False, "error": "Name is required"}
    if not EMAIL_PATTERN.match(email):
        return {"valid": False, "error": "Email is invalid"}
    if not age_raw.isdigit():
        return {"valid": False, "error": "Age must be an integer"}

    age = int(age_raw)
    if age < 0 or age > 120:
        return {"valid": False, "error": "Age must be between 0 and 120"}

    return {"valid": True, "record": {"name": name, "email": email, "age": age}}


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "Upload a CSV file to POST /import and read valid records from GET /data"
    }


@app.get("/data")
def get_data() -> Dict[str, object]:
    return {
        "count": len(stored_records),
        "records": [record.model_dump() for record in stored_records],
    }


@app.post("/import")
async def import_csv(file: UploadFile = File(...)) -> StreamingResponse:
    raw_bytes = await file.read()
    decoded_text = raw_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(decoded_text))
    pending_records: List[Record] = []

    def event_stream() -> Generator[str, None, None]:
        summary = {"processed": 0, "accepted": 0, "rejected": 0}
        first_data_row_seen = False
        next_record_id = len(stored_records) + 1

        for line_number, row in enumerate(reader, start=1):
            if not first_data_row_seen:
                normalized = [column.strip().lower() for column in row]
                if normalized == EXPECTED_HEADER:
                    yield json.dumps({"line": line_number, "status": "header", "columns": row}) + "\n"
                    first_data_row_seen = True
                    continue
                first_data_row_seen = True

            if not row or not any(cell.strip() for cell in row):
                yield json.dumps({"line": line_number, "status": "skipped", "reason": "blank row"}) + "\n"
                continue

            summary["processed"] += 1
            validation = validate_row(row)
            if not validation["valid"]:
                summary["rejected"] += 1
                yield json.dumps(
                    {
                        "line": line_number,
                        "status": "rejected",
                        "row": row,
                        "error": validation["error"],
                    }
                ) + "\n"
                continue

            record_payload = validation["record"]
            record = Record(id=next_record_id, **record_payload)
            next_record_id += 1
            pending_records.append(record)
            summary["accepted"] += 1
            yield json.dumps(
                {
                    "line": line_number,
                    "status": "accepted",
                    "record": record.model_dump(),
                }
            ) + "\n"

        stored_records.extend(pending_records)
        yield json.dumps({"summary": summary, "stored_total": len(stored_records)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
