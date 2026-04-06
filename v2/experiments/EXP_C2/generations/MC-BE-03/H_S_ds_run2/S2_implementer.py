from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
from datetime import datetime

app = FastAPI()

# Models
class Task(BaseModel):
    id: str
    text: str
    column: str
    order: int
    last_moved_by: str
    version: int

class BoardState(BaseModel):
    tasks: Dict[str, Task]
    column_order: Dict[str, List[str]]
    current_user: str
    connected_users: List[str]

class MoveRequest(BaseModel):
    task_id: str
    from_column: str
    to_column: str
    new_order: int
    user_id: str

class AddTaskRequest(BaseModel):
    text: str
    user_id: str

# Initial state
initial_tasks = {
    "1": Task(id="1", text="Design review", column="todo", order=0, last_moved_by="user1", version=1),
    "2": Task(id="2", text="Implement drag", column="todo", order=1, last_moved_by="user1", version=1),
    "3": Task(id="3", text="Write tests", column="inProgress", order=0, last_moved_by="user1", version=1),
    "4": Task(id="4", text="Deploy to prod", column="done", order=0, last_moved_by="user1", version=1)
}

initial_column_order = {
    "todo": ["1", "2"],
    "inProgress": ["3"],
    "done": ["4"]
}

board_state = BoardState(
    tasks=initial_tasks,
    column_order=initial_column_order,
    current_user="user1",
    connected_users=["user1", "user2"]
)

@app.get("/board")
async def get_board() -> BoardState:
    return board_state

@app.post("/tasks")
async def add_task(request: AddTaskRequest) -> Task:
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    new_task = Task(
        id=task_id,
        text=request.text,
        column="todo",
        order=len(board_state.column_order["todo"]),
        last_moved_by=request.user_id,
        version=1
    )
    
    board_state.tasks[task_id] = new_task
    board_state.column_order["todo"].append(task_id)
    
    return new_task

@app.put("/tasks/{task_id}/move")
async def move_task(task_id: str, request: MoveRequest):
    if task_id not in board_state.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = board_state.tasks[task_id]
    
    # Remove from old column
    if task_id in board_state.column_order[request.from_column]:
        board_state.column_order[request.from_column].remove(task_id)
    
    # Add to new column at position
    board_state.column_order[request.to_column].insert(request.new_order, task_id)
    
    # Update task
    task.column = request.to_column
    task.order = request.new_order
    task.last_moved_by = request.user_id
    task.version += 1
    
    return {"message": "Task moved successfully"}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in board_state.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return board_state.tasks[task_id]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
