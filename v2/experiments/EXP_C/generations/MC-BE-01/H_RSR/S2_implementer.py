from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
import asyncio
import uuid
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field

EventType = Literal[
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_retrying",
    "task_exhausted"
]

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]

class EventStore:
    def __init__(self):
        self._events: List[Event] = []
        self._task_index: Dict[str, List[Event]] = {}
        self._idempotency_index: Dict[str, str] = {}
    
    def append(self, event: Event) -> None:
        self._events.append(event)
        
        if event.task_id not in self._task_index:
            self._task_index[event.task_id] = []
        self._task_index[event.task_id].append(event)
    
    def get_events(self, task_id: str) -> List[Event]:
        return self._task_index.get(task_id, [])
    
    def reconstruct(self, task_id: str) -> Optional['TaskState']:
        events = self.get_events(task_id)
        if not events:
            return None
        
        state = TaskState(
            task_id=task_id,
            payload=events[0].data.get('payload', {}),
            created_at=events[0].timestamp
        )
        
        for event in events:
            if event.event_type == "task_started":
                state.status = "running"
            elif event.event_type == "task_completed":
                state.status = "completed"
            elif event.event_type == "task_failed":
                state.status = "failed"
                state.error = event.data.get('error')
                state.retries += 1
            elif event.event_type == "task_retrying":
                state.status = "pending"
                state.retries += 1
            elif event.event_type == "task_exhausted":
                state.status = "exhausted"
            
            state.events_count += 1
            state.updated_at = event.timestamp
        
        return state
    
    def get_task_id_by_idempotency_key(self, key: str) -> Optional[str]:
        return self._idempotency_index.get(key)
    
    def register_idempotency_key(self, key: str, task_id: str) -> None:
        self._idempotency_index[key] = task_id

class TaskState(BaseModel):
    task_id: str
    status: str = "pending"
    payload: Dict[str, Any]
    retries: int = 0
    events_count: int = 0
    created_at: str
    updated_at: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class CreateTaskRequest(BaseModel):
    idempotency_key: str = Field(..., description="Unique key to prevent duplicate submissions")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    max_retries: int = Field(3, ge=0, description="Maximum number of retry attempts")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    payload: Dict[str, Any]
    retries: int
    events_count: int
    created_at: str
    updated_at: Optional[str] = None


class TaskQueueWorker:
    def __init__(self, event_store: EventStore, queue: asyncio.Queue):
        self.event_store = event_store
        self.queue = queue
        self.worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        self.worker_task = asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
    
    async def _worker_loop(self):
        while True:
            task_id = await self.queue.get()
            
            try:
                state = self.event_store.reconstruct(task_id)
                if not state:
                    continue
                
                start_event = Event(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="task_started",
                    timestamp=datetime.now().isoformat(),
                    data={"timestamp": datetime.now().isoformat()}
                )
                self.event_store.append(start_event)
                
                await self._process_task(task_id, state)
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await self._handle_task_failure(task_id, e)
            finally:
                self.queue.task_done()
    
    async def _process_task(self, task_id: str, state: TaskState):
        await asyncio.sleep(0.5 + (state.retries * 0.1))
        
        success_rate = 0.8 - (state.retries * 0.1)
        if success_rate < 0.1:
            success_rate = 0.1
        
        import random
        if random.random() < success_rate:
            complete_event = Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_completed",
                timestamp=datetime.now().isoformat(),
                data={"completed_at": datetime.now().isoformat()}
            )
            self.event_store.append(complete_event)
        else:
            raise Exception(f"Simulated task failure on retry {state.retries}")
    
    async def _handle_task_failure(self, task_id: str, error: Exception):
        state = self.event_store.reconstruct(task_id)
        if not state:
            return
        
        if state.retries >= state.payload.get('max_retries', 3):
            exhausted_event = Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_exhausted",
                timestamp=datetime.now().isoformat(),
                data={
                    "error": str(error),
                    "final_retries": state.retries,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.event_store.append(exhausted_event)
        else:
            failed_event = Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_failed",
                timestamp=datetime.now().isoformat(),
                data={
                    "error": str(error),
                    "retry_count": state.retries,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.event_store.append(failed_event)
            
            retry_event = Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_retrying",
                timestamp=datetime.now().isoformat(),
                data={
                    "retry_count": state.retries + 1,
                    "backoff_seconds": 1.0 * (2 ** state.retries),
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.event_store.append(retry_event)
            
            backoff = 1.0 * (2 ** state.retries)
            await asyncio.sleep(backoff)
            await self.queue.put(task_id)


class TaskQueueService:
    def __init__(self):
        self.event_store = EventStore()
        self.queue = asyncio.Queue()
        self.worker = TaskQueueWorker(self.event_store, self.queue)
        self._lock = asyncio.Lock()
    
    async def create_task(self, request: CreateTaskRequest) -> str:
        async with self._lock:
            existing_task_id = self.event_store.get_task_id_by_idempotency_key(request.idempotency_key)
            if existing_task_id:
                return existing_task_id
            
            task_id = str(uuid.uuid4())
            
            create_event = Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_created",
                timestamp=datetime.now().isoformat(),
                data={
                    "payload": request.payload,
                    "max_retries": request.max_retries,
                    "idempotency_key": request.idempotency_key,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.event_store.append(create_event)
            
            self.event_store.register_idempotency_key(request.idempotency_key, task_id)
            
            await self.queue.put(task_id)
            
            return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.event_store.reconstruct(task_id)
    
    def list_tasks(self, status_filter: Optional[str] = None) -> List[TaskState]:
        tasks = []
        for task_id in self.event_store._task_index.keys():
            state = self.event_store.reconstruct(task_id)
            if state and (not status_filter or state.status == status_filter):
                tasks.append(state)
        
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks


def get_task_service() -> TaskQueueService:
    if not hasattr(app.state, 'task_service'):
        app.state.task_service = TaskQueueService()
    return app.state.task_service


task_service: Optional[TaskQueueService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = get_task_service()
    await service.worker.start()
    yield
    await service.worker.stop()


app = FastAPI(
    title="Event-Sourced Task Queue API",
    description="Task queue with event sourcing and idempotent endpoints",
    version="1.0.0",
    lifespan=lifespan
)


@app.on_event("startup")
async def startup_event():
    service = get_task_service()
    await service.worker.start()


@app.on_event("shutdown")
async def shutdown_event():
    service = get_task_service()
    await service.worker.stop()


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    service: TaskQueueService = Depends(get_task_service)
):
    try:
        task_id = await service.create_task(request)
        task_state = service.get_task(task_id)
        if not task_state:
            raise HTTPException(status_code=500, detail="Task creation failed")
        
        return TaskResponse(
            task_id=task_id,
            status=task_state.status,
            payload=task_state.payload,
            retries=task_state.retries,
            events_count=task_state.events_count,
            created_at=task_state.created_at,
            updated_at=task_state.updated_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: str,
    service: TaskQueueService = Depends(get_task_service)
):
    task_state = service.get_task(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        task_id=task_state.task_id,
        status=task_state.status,
        payload=task_state.payload,
        retries=task_state.retries,
        events_count=task_state.events_count,
        created_at=task_state.created_at,
        updated_at=task_state.updated_at
    )


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    service: TaskQueueService = Depends(get_task_service)
):
    tasks = service.list_tasks(status)
    return [
        TaskResponse(
            task_id=task.task_id,
            status=task.status,
            payload=task.payload,
            retries=task.retries,
            events_count=task.events_count,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        for task in tasks
    ]


@app.get("/tasks/{task_id}/events", response_model=List[Event])
async def get_task_events(
    task_id: str,
    service: TaskQueueService = Depends(get_task_service)
):
    events = service.event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return events


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)