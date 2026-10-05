import sqlite3
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

DATABASE_FILE = "tasks.db"


def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Enables column access by name
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Stage 0: Create table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
        """
        )

        # Insert 3 default tasks ONLY if table is empty
        cursor.execute("SELECT COUNT(*) as count FROM tasks")
        count = cursor.fetchone()["count"]
        if count == 0:
            cursor.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Review PRs", 0),
                    ("Write documentation", 1),
                    ("Deploy staging build", 0),
                ],
            )
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task API",
    version="1.0",
    description="SQLite-backed CRUD API for managing tasks.",
    lifespan=lifespan,
)


# --- Schemas ---
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Task title cannot be empty")


class TaskUpdate(BaseModel):
    title: str = Field(..., min_length=1, description="Task title cannot be empty")
    done: bool = Field(..., description="Completion status")


def row_to_task(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


# --- Front Door & Health ---
@app.get("/", tags=["General"], status_code=status.HTTP_200_OK)
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", tags=["General"], status_code=status.HTTP_200_OK)
def health():
    return {"status": "ok"}


# --- Stage 1: Read Endpoints ---
@app.get("/tasks", tags=["Tasks"], status_code=status.HTTP_200_OK)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter tasks by completion status"),
    search: Optional[str] = Query(None, description="Search term in task title"),
):
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [row_to_task(row) for row in rows]


@app.get("/tasks/{id}", tags=["Tasks"], status_code=status.HTTP_200_OK)
def get_task(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Task {id} not found"},
            )
        return row_to_task(row)


# --- Stage 2: Create Endpoint ---
@app.post("/tasks", tags=["Tasks"], status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title cannot be whitespace or empty"},
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, done) VALUES (?, 0)",
            (clean_title,),
        )
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        return row_to_task(row)


# --- Stage 3: Update & Delete Endpoints ---
@app.put("/tasks/{id}", tags=["Tasks"], status_code=status.HTTP_200_OK)
def update_task(id: int, payload: TaskUpdate):
    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title cannot be whitespace or empty"},
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Task {id} not found"},
            )

        cursor.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (clean_title, 1 if payload.done else 0, id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
        return row_to_task(cursor.fetchone())


@app.delete("/tasks/{id}", tags=["Tasks"], status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Task {id} not found"},
            )

        cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Extras: Statistics Endpoint ---
@app.get("/stats", tags=["General"], status_code=status.HTTP_200_OK)
def stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as done_count FROM tasks WHERE done = 1")
        done_count = cursor.fetchone()["done_count"]

        return {
            "total": total,
            "done": done_count,
            "open": total - done_count,
        }