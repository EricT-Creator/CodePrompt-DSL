import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ==================== Data Models ====================

class TaskRequest(BaseModel):
    idempotency_key: str
    max_retries: int = 3
    payload: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    task_id: str
    status: str
    retries: int
    max_retries: int
    result: Optional[Any] = None
    created_at: float
    updated_at: float


class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: float
    payload: Dict[str, Any]


class ReplayResponse(BaseModel):
    task_id: str
    current_state: TaskResponse
    events_applied: int


# ==================== Internal Data Classes ====================

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskState:
    task_id: str
    idempotency_key: str
    status: str
    retries: int
    max_retries: int
    result: Optional[Any] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ==================== Event Store ====================

class EventStore:
    def __init__(self):
        self._events: Dict[str, List[Event]] = {}
        self._idempotency_index: Dict[str, str] = {}
    
    def append_event(self, task_id: str, event_type: str, payload: Dict[str, Any] = None) -> Event:
        if payload is None:
            payload = {}
        
        event = Event(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            timestamp=time.time(),
            payload=payload
        )
        
        if task_id not in self._events:
            self._events[task_id] = []
        
        self._events[task_id].append(event)
        return event
    
    def get_events(self, task_id: str) -> List[Event]:
        return self._events.get(task_id, [])
    
    def register_idempotency_key(self, key: str, task_id: str) -> bool:
        if key in self._idempotency_index:
            return False
        self._idempotency_index[key] = task_id
        return True
    
    def get_task_id_by_key(self, key: str) -> Optional[str]:
        return self._idempotency_index.get(key)


# ==================== State Derivation ====================

def derive_state_from_events(events: List[Event]) -> TaskState:
    if not events:
        raise ValueError("No events to derive state from")
    
    # Get task info from first event (SUBMITTED)
    first_event = events[0]
    task_id = first_event.task_id
    idempotency_key = first_event.payload.get('idempotency_key', '')
    max_retries = first_event.payload.get('max_retries', 3)
    
    state = TaskState(
        task_id=task_id,
        idempotency_key=idempotency_key,
        status='PENDING',
        retries=0,
        max_retries=max_retries,
        created_at=first_event.timestamp,
        updated_at=first_event.timestamp
    )
    
    retry_scheduled_count = 0
    
    for event in events:
        state.updated_at = event.timestamp
        
        if event.event_type == 'SUBMITTED':
            state.status = 'PENDING'
        
        elif event.event_type == 'QUEUED':
            state.status = 'QUEUED'
        
        elif event.event_type == 'PROCESSING':
            state.status = 'PROCESSING'
        
        elif event.event_type == 'SUCCEEDED':
            state.status = 'SUCCEEDED'
            state.result = event.payload.get('result')
        
        elif event.event_type == 'FAILED':
            state.status = 'FAILED'
            state.result = event.payload.get('error')
        
        elif event.event_type == 'RETRY_SCHEDULED':
            retry_scheduled_count += 1
            state.retries = retry_scheduled_count
            state.status = 'RETRY_SCHEDULED'
        
        elif event.event_type == 'EXHAUSTED':
            state.status = 'EXHAUSTED'
    
    return state


# ==================== Task Worker ====================

class TaskWorker:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.queue = asyncio.Queue()
        self._worker_task = None
        self.base_delay = 1.0
        self.backoff_multiplier = 2.0
        self.max_delay = 30.0
    
    def start(self):
        self._worker_task = asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def submit_task(self, task_id: str, payload: Dict[str, Any]):
        await self.queue.put(task_id)
    
    async def _worker_loop(self):
        while True:
            try:
                task_id = await self.queue.get()
                await self._process_task(task_id)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task_id: str):
        events = self.event_store.get_events(task_id)
        if not events:
            return
        
        # Mark as processing
        self.event_store.append_event(task_id, 'PROCESSING')
        
        try:
            # Simulate some work
            await asyncio.sleep(1.0)
            
            # Random success/failure (80% success rate for demo)
            import random
            if random.random() < 0.8:
                result = {"message": "Task completed successfully", "value": random.randint(1, 100)}
                self.event_store.append_event(task_id, 'SUCCEEDED', {"result": result})
            else:
                error_msg = f"Simulated failure at {datetime.now().isoformat()}"
                self.event_store.append_event(task_id, 'FAILED', {"error": error_msg})
                
                # Check if we should retry
                events = self.event_store.get_events(task_id)
                state = derive_state_from_events(events)
                
                retries_used = sum(1 for e in events if e.event_type == 'RETRY_SCHEDULED')
                if retries_used < state.max_retries:
                    await self._schedule_retry(task_id, retries_used)
                else:
                    self.event_store.append_event(task_id, 'EXHAUSTED')
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.event_store.append_event(task_id, 'FAILED', {"error": error_msg})
    
    async def _schedule_retry(self, task_id: str, retry_count: int):
        delay = min(
            self.base_delay * (self.backoff_multiplier ** retry_count),
            self.max_delay
        )
        
        # Add jitter (±10%)
        import random
        jitter = random.uniform(0.9, 1.1)
        delay *= jitter
        
        self.event_store.append_event(task_id, 'RETRY_SCHEDULED', {
            "retry_count": retry_count + 1,
            "delay": delay
        })
        
        # Schedule the retry
        async def delayed_requeue():
            await asyncio.sleep(delay)
            await self.submit_task(task_id, {})
        
        asyncio.create_task(delayed_requeue())


# ==================== FastAPI Application ====================

app = FastAPI(title="Event-Sourced Task Queue")
event_store = EventStore()
worker = TaskWorker(event_store)


@app.on_event("startup")
async def startup_event():
    worker.start()


@app.on_event("shutdown")
async def shutdown_event():
    await worker.stop()


@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest):
    # Check idempotency
    existing_task_id = event_store.get_task_id_by_key(request.idempotency_key)
    if existing_task_id:
        events = event_store.get_events(existing_task_id)
        if events:
            state = derive_state_from_events(events)
            return TaskResponse(
                task_id=state.task_id,
                status=state.status,
                retries=state.retries,
                max_retries=state.max_retries,
                result=state.result,
                created_at=state.created_at,
                updated_at=state.updated_at
            )
    
    # Create new task
    task_id = str(uuid.uuid4())
    
    event_store.register_idempotency_key(request.idempotency_key, task_id)
    
    event_store.append_event(task_id, 'SUBMITTED', {
        'idempotency_key': request.idempotency_key,
        'max_retries': request.max_retries,
        'payload': request.payload
    })
    
    event_store.append_event(task_id, 'QUEUED')
    
    # Submit to worker
    await worker.submit_task(task_id, request.payload)
    
    events = event_store.get_events(task_id)
    state = derive_state_from_events(events)
    
    return TaskResponse(
        task_id=state.task_id,
        status=state.status,
        retries=state.retries,
        max_retries=state.max_retries,
        result=state.result,
        created_at=state.created_at,
        updated_at=state.updated_at
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    events = event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    
    state = derive_state_from_events(events)
    
    return TaskResponse(
        task_id=state.task_id,
        status=state.status,
        retries=state.retries,
        max_retries=state.max_retries,
        result=state.result,
        created_at=state.created_at,
        updated_at=state.updated_at
    )


@app.get("/tasks/{task_id}/events", response_model=List[EventResponse])
async def get_task_events(task_id: str):
    events = event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return [
        EventResponse(
            event_id=e.event_id,
            task_id=e.task_id,
            event_type=e.event_type,
            timestamp=e.timestamp,
            payload=e.payload
        )
        for e in events
    ]


@app.post("/tasks/{task_id}/replay", response_model=ReplayResponse)
async def replay_task_events(task_id: str):
    events = event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    
    state = derive_state_from_events(events)
    
    return ReplayResponse(
        task_id=task_id,
        current_state=TaskResponse(
            task_id=state.task_id,
            status=state.status,
            retries=state.retries,
            max_retries=state.max_retries,
            result=state.result,
            created_at=state.created_at,
            updated_at=state.updated_at
        ),
        events_applied=len(events)
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


# ==================== Main Execution ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)