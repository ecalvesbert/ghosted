from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.brokers import BROKER_REGISTRY
from app.database import get_db
from app.models.user import UserProfile
from app.models.batch import RemovalBatch
from app.models.removal import RemovalRequest
from app.schemas.removal import (
    RemovalCreateRequest,
    RemovalRequestResponse,
    RemovalBatchResponse,
    RemovalSummaryResponse,
)
from app.services.auth import get_current_user
from app.services.removal_engine import run_removal_batch_sync

router = APIRouter(prefix="/api/removals", tags=["removals"])


@router.post("", response_model=RemovalBatchResponse, status_code=201)
def create_removal_batch(
    req: RemovalCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate broker slugs
    valid_brokers = [b for b in req.brokers if b in BROKER_REGISTRY]
    if not valid_brokers:
        raise HTTPException(
            status_code=400,
            detail="No valid brokers specified",
            headers={"code": "INVALID_BROKERS"},
        )

    # Enforce 1 active batch per user
    active = db.query(RemovalBatch).filter(
        RemovalBatch.user_id == current_user.id,
        RemovalBatch.status.in_(["pending", "running"]),
    ).with_for_update().first()
    if active:
        return JSONResponse(
            status_code=409,
            content={"detail": "A removal batch is already running", "code": "BATCH_ALREADY_RUNNING"},
        )

    batch = RemovalBatch(
        user_id=current_user.id,
        status="pending",
        brokers_targeted=valid_brokers,
        brokers_completed=[],
        brokers_failed=[],
        total_removals=0,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Run removal engine in background thread
    background_tasks.add_task(run_removal_batch_sync, str(batch.id), str(current_user.id), valid_brokers)

    return batch


@router.get("", response_model=list[RemovalRequestResponse])
def list_removals(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removals = db.query(RemovalRequest).filter(
        RemovalRequest.user_id == current_user.id
    ).order_by(RemovalRequest.created_at.desc()).all()
    return removals


@router.get("/batches", response_model=list[RemovalBatchResponse])
def list_batches(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batches = db.query(RemovalBatch).filter(
        RemovalBatch.user_id == current_user.id
    ).order_by(RemovalBatch.created_at.desc()).all()
    return batches


@router.get("/batches/{batch_id}", response_model=RemovalBatchResponse)
def get_batch(
    batch_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.query(RemovalBatch).filter(
        RemovalBatch.id == batch_id,
        RemovalBatch.user_id == current_user.id,
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found", headers={"code": "NOT_FOUND"})
    return batch


@router.get("/summary", response_model=RemovalSummaryResponse)
def removal_summary(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removals = db.query(RemovalRequest).filter(
        RemovalRequest.user_id == current_user.id
    ).all()

    summary = {
        "total": 0,
        "pending": 0,
        "in_progress": 0,
        "submitted": 0,
        "needs_verification": 0,
        "confirmed": 0,
        "failed": 0,
    }
    for r in removals:
        summary["total"] += 1
        if r.status in summary:
            summary[r.status] += 1

    return summary


@router.get("/{removal_id}", response_model=RemovalRequestResponse)
def get_removal(
    removal_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removal = db.query(RemovalRequest).filter(
        RemovalRequest.id == removal_id,
        RemovalRequest.user_id == current_user.id,
    ).first()
    if not removal:
        raise HTTPException(status_code=404, detail="Removal request not found", headers={"code": "NOT_FOUND"})
    return removal


@router.post("/{removal_id}/recheck", response_model=RemovalRequestResponse)
def recheck_removal(
    removal_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removal = db.query(RemovalRequest).filter(
        RemovalRequest.id == removal_id,
        RemovalRequest.user_id == current_user.id,
    ).first()
    if not removal:
        raise HTTPException(status_code=404, detail="Removal request not found", headers={"code": "NOT_FOUND"})

    # Re-run the opt-out for this single broker
    from app.services.removal_engine import run_removal_batch_sync

    # Create a mini-batch for the recheck
    batch = RemovalBatch(
        user_id=current_user.id,
        status="pending",
        brokers_targeted=[removal.broker],
        brokers_completed=[],
        brokers_failed=[],
        total_removals=0,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(run_removal_batch_sync, str(batch.id), str(current_user.id), [removal.broker])

    return removal
