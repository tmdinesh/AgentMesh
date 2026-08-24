from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=List[TaskResponse])
def get_all_tasks(db: Session = Depends(get_db)):
    """Returns all available benchmark tasks."""
    return db.query(Task).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_by_id(task_id: str, db: Session = Depends(get_db)):
    """Returns a specific benchmark task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task
