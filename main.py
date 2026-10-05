from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="1.0",
    description="In-memory CRUD API for managing tasks.",
)

# In-memory store
tasks_db = [
    {"id": 1, "title": "Review PRs", "done": False},
    {"id": 2, "title": "Write documentation", "done": True},
    {"id": 3, "title": "Deploy staging build", "done": False},
]
current_id = 3


# --- Schemas ---
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Task title cannot be empty")


class TaskUpdate(BaseModel):
    title: str = Field(..., min_length=1, description="Task title cannot be empty")
    done: bool = Field(..., description="Completion status")


# --- Stage 1: Front Door & Health ---
@app.get(
    "/",
    tags=["General"],
    summary="API Front Door",
    status_code=status.HTTP_200_OK,
)
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get(
    "/health",
    tags=["General"],
    summary="Health Check",
    status_code=status.HTTP_200_OK,
)
def health():
    return {"status": "ok"}


# --- Stage 2: Read Endpoints ---
@app.get(
    "/tasks",
    tags=["Tasks"],
    summary="List all tasks",
    status_code=status.HTTP_200_OK,
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter tasks by completion status"),
    search: Optional[str] = Query(None, description="Search term in task title"),
):
    results = tasks_db
    if done is not None:
        results = [t for t in results if t["done"] == done]
    if search:
        results = [t for t in results if search.lower() in t["title"].lower()]
    return results


@app.get(
    "/tasks/{id}",
    tags=["Tasks"],
    summary="Get single task",
    status_code=status.HTTP_200_OK,
)
def get_task(id: int):
    for task in tasks_db:
        if task["id"] == id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": f"Task {id} not found"},
    )


# --- Stage 3: Create Endpoint ---
@app.post(
    "/tasks",
    tags=["Tasks"],
    summary="Create a new task",
    status_code=status.HTTP_201_CREATED,
)
def create_task(payload: TaskCreate):
    global current_id
    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title cannot be whitespace or empty"},
        )

    current_id += 1
    new_task = {"id": current_id, "title": clean_title, "done": False}
    tasks_db.append(new_task)
    return new_task


# --- Stage 4: Update & Delete Endpoints ---
@app.put(
    "/tasks/{id}",
    tags=["Tasks"],
    summary="Update a task",
    status_code=status.HTTP_200_OK,
)
def update_task(id: int, payload: TaskUpdate):
    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title cannot be whitespace or empty"},
        )

    for task in tasks_db:
        if task["id"] == id:
            task["title"] = clean_title
            task["done"] = payload.done
            return task

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": f"Task {id} not found"},
    )


@app.delete(
    "/tasks/{id}",
    tags=["Tasks"],
    summary="Delete a task",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(id: int):
    for index, task in enumerate(tasks_db):
        if task["id"] == id:
            tasks_db.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": f"Task {id} not found"},
    )