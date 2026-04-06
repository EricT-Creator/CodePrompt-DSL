from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import time
import asyncio
from dataclasses import dataclass
from typing import Any
import random

app = FastAPI(title="Event-Sourced Task Queue")

# ===================== Data Models =====================

class TaskSubmission(BaseModel):
    idempotency_key: str
    payload: dict
    max_retries: int = 3
    backoff_base: float = 1.0

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    payload: dict
    retry_count: int
    last_error: Optional[str] = None

class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    data: dict

# ===================== Event Store =====================

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: str
    timestamp: datetime
    data: dict

event_store: List[Event] = []
task_index: Dict[str, List[int]] = {}
idempotency_map: Dict[str, str] = {}

# ===================== Event Store Functions =====================

def append_event(task_id: str, event_type: str, data: dict) -> Event:
    event = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=datetime.now(),
        data=data
    )
    event_store.append(event)
    
    if task_id not in task_index:
        task_index[task_id] = []
    task_index[task_id].append(len(event_store) - 1)
    
    return event

def get_events_for_task(task_id: str) -> List[Event]:
    if task_id not in task_index:
        return []
    
    return [event_store[i] for i in task_index[task_id]]

def derive_task_state(task_id: str) -> Optional[TaskResponse]:
    events = get_events_for_task(task_id)
    if not events:
        return None
    
    state = {
        "task_id": task_id,
        "status": "pending",
        "created_at": events[0].timestamp.isoformat(),
        "payload": {},
        "retry_count": 0,
        "last_error": None
    }
    
    for event in events:
        if event.event_type == "TASK_CREATED":
            state["payload"] = event.data.get("payload", {})
            state["status"] = "queued"
        
        elif event.event_type == "TASK_QUEUED":
            state["status"] = "queued"
        
        elif event.event_type == "TASK_STARTED":
            state["status"] = "running"
            if "attempt" in event.data:
                state["retry_count"] = event.data["attempt"] - 1
        
        elif event.event_type == "TASK_FAILED":
            state["status"] = "failed"
            state["last_error"] = event.data.get("error", "Unknown error")
            if "attempt" in event.data:
                state["retry_count"] = event.data["attempt"]
        
        elif event.event_type == "TASK_SUCCEEDED":
            state["status"] = "completed"
        
        elif event.event_type == "TASK_RETRY_SCHEDULED":
            state["status"] = "retrying"
        
        elif event.event_type == "TASK_EXHAUSTED":
            state["status"] = "failed"
            state["last_error"] = "All retries exhausted"
    
    return TaskResponse(**state)

# ===================== Async Queue and Worker =====================

task_queue = asyncio.Queue()

async def worker():
    while True:
        try:
            task_info = await task_queue.get()
            task_id = task_info["task_id"]
            max_retries = task_info["max_retries"]
            backoff_base = task_info["backoff_base"]
            
            # Record task start
            append_event(task_id, "TASK_STARTED", {"attempt": task_info["attempt"]})
            
            # Simulate work with random success/failure
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            if random.random() < 0.7:  # 70% success rate
                append_event(task_id, "TASK_SUCCEEDED", {"result": {"success": True}})
                await asyncio.sleep(0.1)  # Simulate network latency
                append_event(task_id, "CONFIRM_OP", {"op_id": f"op-{task_id}"})
            else:
                error_msg = f"Simulated failure at attempt {task_info['attempt']}"
                append_event(task_id, "TASK_FAILED", {
                    "error": error_msg,
                    "attempt": task_info["attempt"]
                })
                
                if task_info["attempt"] < max_retries:
                    delay = backoff_base * (2 ** (task_info["attempt"] - 1))
                    delay = min(delay, 60.0)  # Cap at 60 seconds
                    
                    append_event(task_id, "TASK_RETRY_SCHEDULED", {
                        "next_attempt": task_info["attempt"] + 1,
                        "delay": delay
                    })
                    
                    await asyncio.sleep(delay)
                    await task_queue.put({
                        "task_id": task_id,
                        "max_retries": max_retries,
                        "backoff_base": backoff_base,
                        "attempt": task_info["attempt"] + 1
                    })
                else:
                    append_event(task_id, "TASK_EXHAUSTED", {
                        "total_attempts": task_info["attempt"]
                    })
            
            task_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Worker error: {e}")

# ===================== API Endpoints =====================

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker())

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(submission: TaskSubmission, background_tasks: BackgroundTasks):
    # Check idempotency
    if submission.idempotency_key in idempotency_map:
        task_id = idempotency_map[submission.idempotency_key]
        state = derive_task_state(task_id)
        if state:
            return state
    
    # Create new task
    task_id = str(uuid.uuid4())
    idempotency_map[submission.idempotency_key] = task_id
    
    append_event(task_id, "TASK_CREATED", {
        "payload": submission.payload,
        "max_retries": submission.max_retries,
        "backoff_base": submission.backack_base
    })
    
    append_event(task_id, "TASK_QUEUED", {})
    
    # Enqueue task
    await task_queue.put({
        "task_id": task_id,
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base,
        "attempt": 1
    })
    
    state = derive_task_state(task_id)
    if not state:
        raise HTTPException(status_code=500, detail="Failed to create task")
    
    return state

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    state = derive_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")
    return state

@app.get("/tasks/{task_id}/events", response_model=List[EventResponse])
async def get_task_events(task_id: str):
    events = get_events_for_task(task_id)
    return [
        EventResponse(
            event_id=event.event_id,
            task_id=event.task_id,
            event_type=event.event_type,
            timestamp=event.timestamp.isoformat(),
            data=event.data
        )
        for event in events
    ]

@app.post("/tasks/{task_id}/replay")
async def replay_task_events(task_id: str):
    events = get_events_for_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="No events found for task")
    
    # Just return the events, demonstrating the replay concept
    return {
        "task_id": task_id,
        "events": [
            EventResponse(
                event_id=event.event_id,
                task_id=event.task_id,
                event_type=event.event_type,
                timestamp=event.timestamp.isoformat(),
                data=event.data
            )
            for event in events
        ],
        "derived_state": derive_task_state(task_id).dict() if derive_task_state(task_id) else None
    }

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    tasks = []
    for task_id in task_index:
        state = derive_task_state(task_id)
        if state:
            tasks.append(state)
    return tasks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)