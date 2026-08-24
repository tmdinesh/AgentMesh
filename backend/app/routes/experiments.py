from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.experiment import Experiment
from app.models.message import Message
from app.schemas.experiment import (
    ExperimentCreate,
    BatchExperimentCreate,
    ExperimentResponse,
    ExperimentDetailResponse,
)
from app.schemas.message import MessageResponse
from app.schemas.network import NetworkMetrics
from app.services.experiment_service import experiment_service

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentDetailResponse)
async def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    """Runs a single multi-agent topology experiment."""
    try:
        exp = await experiment_service.run_experiment(payload, db)
        return exp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Experiment execution failed: {e}")


@router.post("/batch", response_model=List[ExperimentResponse])
async def create_batch_experiments(payload: BatchExperimentCreate, db: Session = Depends(get_db)):
    """Runs batch repetitions across topologies."""
    try:
        exps = await experiment_service.run_batch_experiments(payload, db)
        return exps
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch execution failed: {e}")


@router.get("", response_model=List[ExperimentResponse])
def list_experiments(
    topology: Optional[str] = Query(None, description="Filter by topology (STAR, CHAIN, MESH, UNCONSTRAINED)"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    db: Session = Depends(get_db)
):
    """Lists all past experimental runs with optional filtering."""
    query = db.query(Experiment).options(joinedload(Experiment.task))
    if topology:
        query = query.filter(Experiment.topology == topology.upper())
    if success is not None:
        query = query.filter(Experiment.success == success)
    return query.order_by(Experiment.created_at.desc()).all()


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment_details(experiment_id: str, db: Session = Depends(get_db)):
    """Returns details and message transcript for an experiment."""
    exp = db.query(Experiment).options(joinedload(Experiment.task), joinedload(Experiment.messages)).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return exp


@router.get("/{experiment_id}/messages", response_model=List[MessageResponse])
def get_experiment_messages(experiment_id: str, db: Session = Depends(get_db)):
    """Returns the chronological agent message log."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return exp.messages


@router.get("/{experiment_id}/network", response_model=NetworkMetrics)
def get_experiment_network(experiment_id: str, db: Session = Depends(get_db)):
    """Returns NetworkX network metrics and graph data for an experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    metrics_data = exp.network_metrics
    if not metrics_data:
        raise HTTPException(status_code=404, detail="Network metrics unavailable for this experiment.")
    return metrics_data


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    """Deletes an experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    db.delete(exp)
    db.commit()
    return {"status": "deleted", "id": experiment_id}


@router.delete("")
def clear_all_experiments(db: Session = Depends(get_db)):
    """Resets the experimental database."""
    db.query(Message).delete()
    db.query(Experiment).delete()
    db.commit()
    return {"status": "cleared"}
