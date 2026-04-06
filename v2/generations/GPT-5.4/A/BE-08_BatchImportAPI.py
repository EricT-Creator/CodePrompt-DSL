import csv
import io
from typing import Dict, Generator, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

app = FastAPI(title="Batch Import API")

imported_records: List[Dict[str, object]] = []


def is_valid_email(value: str) -> bool:
    value = value.strip()
    if "@" not in value:
        return False
    local, _, domain = value.partition("@")
    return bool(local and domain and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def validate_row(row: Dict[str, str]) -> Dict[str, object]:
    name = (row.get("name") or "").strip()
    email = (row.get("email") or "").strip()
    age_text = (row.get("age") or "").strip()

    if not name:
        raise ValueError("name must be a non-empty string")
    if not is_valid_email(email):
        raise ValueError("email must contain @ and a valid dot-separated domain")

    try:
        age = int(age_text)
    except ValueError as exc:
        raise ValueError("age must be an integer") from exc

    if age < 0 or age > 150:
        raise ValueError("age must be between 0 and 150")

    return {"name": name, "email": email, "age": age}


def process_csv(text: str) -> Generator[str, None, None]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        yield "error: missing CSV header\n"
        return

    total = 0
    success = 0
    failed = 0
    skipped = 0

    for index, row in enumerate(reader, start=1):
        total += 1
        if all(not (value or "").strip() for value in row.values()):
            skipped += 1
            yield f"row {index}: skipped empty row\n"
            continue

        try:
            record = validate_row(row)
        except ValueError as exc:
            failed += 1
            yield f"row {index}: failed - {exc}\n"
            continue

        imported_records.append(record)
        success += 1
        yield f"row {index}: imported - {record['name']} ({record['email']})\n"

    yield (
        f"summary: total={total}, success={success}, failed={failed}, skipped={skipped}\n"
    )


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from None

    return StreamingResponse(process_csv(text), media_type="text/plain; charset=utf-8")


@app.get("/data")
async def get_data() -> Dict[str, List[Dict[str, object]]]:
    return {"records": imported_records}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
