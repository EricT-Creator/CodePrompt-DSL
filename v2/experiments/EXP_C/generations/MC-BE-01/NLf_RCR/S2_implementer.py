import asyncio
import hashlib
import json
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class TaskSubmission(BaseModel):
    idempotency_key: str
    payload: Dict[str, Any]
    max_retries: int = 3
    backoff_base: float = 1.0

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    payload: Dict[str, Any]
    retry_count: int
    last_error: Optional[str]

class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    data: Dict[str, Any]

class Event:
    def __init__(self, event_id: str, task_id: str, event_type: str, data: Dict[str, Any]):
        self.event_id = event_id
        self.task_id = task_id
        self.event_type = event_type
        self.timestamp = datetime.utcnow()
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }

event_store: List[Event] = []
task_index: Dict[str, List[int]] = {}
idempotency_map: Dict[str, str] = {}
task_queue: asyncio.Queue = asyncio.Queue()

worker_task: Optional[asyncio.Task] = None

async def execute_task(task_id: str, payload: Dict[str, Any]) -> tuple[bool, Any, Optional[str]]:
    await asyncio.sleep(0.1)
    if random.random() < 0.3:
        return False, None, "Simulated task failure"
    return True, {"result": f"Processed {payload}"}, None

async def worker_loop():
    while True:
        try:
            task_info = await task_queue.get()
            task_id = task_info["task_id"]
            payload = task_info["payload"]
            max_retries = task_info["max_retries"]
            backoff_base = task_info["backoff_base"]
            
            event = Event(str(uuid.uuid4()), task_id, "TASK_STARTED", {"attempt": 1})
            event_store.append(event)
            task_index.setdefault(task_id, []).append(len(event_store) - 1)
            
            success, result, error = await execute_task(task_id, payload)
            
            if success:
                event = Event(str(uuid.uuid4()), task_id, "TASK_SUCCEEDED", {"result": result})
                event_store.append(event)
                task_index.setdefault(task_id, []).append(len(event_store) - 1)
            else:
                event = Event(str(uuid.uuid4()), task_id, "TASK_FAILED", {"error": error, "attempt": 1})
                event_store.append(event)
                task_index.setdefault(task_id, []).append(len(event_store) - 1)
                
                if max_retries > 0:
                    delay = min(backoff_base * (2 ** 0), 60)
                    event = Event(str(uuid.uuid4()), task_id, "TASK_RETRY_SCHEDULED", {"next_attempt": 2, "delay": delay})
                    event_store.append(event)
                    task_index.setdefault(task_id, []).append(len(event_store) - 1)
                    await asyncio.sleep(delay)
                    await task_queue.put({"task_id": task_id, "payload": payload, "max_retries": max_retries - 1, "backoff_base": backoff_base})
                else:
                    event = Event(str(uuid.uuid4()), task_id, "TASK_EXHAUSTED", {"total_attempts": 1})
                    event_store.append(event)
                    task_index.setdefault(task_id, []).append(len(event_store) - 1)
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    worker_task = asyncio.create_task(worker_loop())
    yield
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

def derive_task_status(task_id: str) -> str:
    if task_id not in task_index:
        return "unknown"
    events = [event_store[i] for i in task_index[task_id]]
    status = "pending"
    for event in events:
        if event.event_type == "TASK_CREATED":
            status = "pending"
        elif event.event_type == "TASK_QUEUED":
            status = "queued"
        elif event.event_type == "TASK_STARTED":
            status = "running"
        elif event.event_type == "TASK_SUCCEEDED":
            status = "completed"
        elif event.event_type == "TASK_FAILED":
            status = "failed"
        elif event.event_type == "TASK_RETRY_SCHEDULED":
            status = "retrying"
        elif event.event_type == "TASK_EXHAUSTED":
            status = "failed"
    return status

def get_task_retry_count(task_id: str) -> int:
    if task_id not in task_index:
        return 0
    events = [event_store[i] for i in task_index[task_id]]
    count = 0
    for event in events:
        if event.event_type in ["TASK_FAILED", "TASK_RETRY_SCHEDULED"]:
            count += 1
    return count

def get_task_last_error(task_id: str) -> Optional[str]:
    if task_id not in task_index:
        return None
    events = [event_store[i] for i in task_index[task_id]]
    for event in reversed(events):
        if event.event_type == "TASK_FAILED":
            return event.data.get("error")
    return None

@app.post("/tasks", response_model=TaskResponse)
async def create_task(submission: TaskSubmission):
    if submission.idempotency_key in idempotency_map:
        task_id = idempotency_map[submission.idempotency_key]
        return TaskResponse(
            task_id=task_id,
            status=derive_task_status(task_id),
            created_at=datetime.utcnow().isoformat(),
            payload=submission.payload,
            retry_count=get_task_retry_count(task_id),
            last_error=get_task_last_error(task_id)
        )
    
    task_id = str(uuid.uuid4())
    idempotency_map[submission.idempotency_key] = task_id
    
    event = Event(str(uuid.uuid4()), task_id, "TASK_CREATED", {
        "payload": submission.payload,
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base
    })
    event_store.append(event)
    task_index.setdefault(task_id, []).append(len(event_store) - 1)
    
    event = Event(str(uuid.uuid4()), task_id, "TASK_QUEUED", {})
    event_store.append(event)
    task_index[task_id].append(len(event_store) - 1)
    
    await task_queue.put({
        "task_id": task_id,
        "payload": submission.payload,
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base
    })
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        created_at=datetime.utcnow().isoformat(),
        payload=submission.payload,
        retry_count=0,
        last_error=None
    )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    
    events = [event_store[i] for i in task_index[task_id]]
    created_event = next((e for e in events if e.event_type == "TASK_CREATED"), None)
    payload = created_event.data.get("payload", {}) if created_event else {}
    
    return TaskResponse(
        task_id=task_id,
        status=derive_task_status(task_id),
        created_at=events[0].timestamp.isoformat() if events else datetime.utcnow().isoformat(),
        payload=payload,
        retry_count=get_task_retry_count(task_id),
        last_error=get_task_last_error(task_id)
    )

@app.get("/tasks/{task_id}/events", response_model=List[EventResponse])
async def get_task_events(task_id: str):
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    
    events = [event_store[i] for i in task_index[task_id]]
    return [EventResponse(**e.to_dict()) for e in events]

@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str):
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    
    events = [event_store[i] for i in task_index[task_id]]
    created_event = next((e for e in events if e.event_type == "TASK_CREATED"), None)
    payload = created_event.data.get("payload", {}) if created_event else {}
    
    return TaskResponse(
        task_id=task_id,
        status=derive_task_status(task_id),
        created_at=events[0].timestamp.isoformat() if events else datetime.utcnow().isoformat(),
        payload=payload,
        retry_count=get_task_retry_count(task_id),
        last_error=get_task_last_error(task_id)
    )

@app.get("/tasks")
async def list_tasks():
    result = []
    for task_id in task_index:
        events = [event_store[i] for i in task_index[task_id]]
        created_event = next((e for e in events if e.event_type == "TASK_CREATED"), None)
        payload = created_event.data.get("payload", {}) if created_event else {}
        result.append({
            "task_id": task_id,
            "status": derive_task_status(task_id),
            "created_at": events[0].timestamp.isoformat() if events else datetime.utcnow().isoformat(),
            "payload": payload
        })
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
