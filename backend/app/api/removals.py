from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.removal import RemovalRequest
from app.schemas.removal import RemovalRequestResponse, RemovalSummaryResponse
from app.services.auth import get_current_user
from app.services.status_tracker import get_removal_summary, get_stale_removals

router = APIRouter(prefix="/api/removals", tags=["removals"])


@router.get("", response_model=list[RemovalRequestResponse])
def list_removals(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removals = db.query(RemovalRequest).filter(
        RemovalRequest.user_id == current_user.id
    ).order_by(RemovalRequest.submitted_at.desc()).all()
    return removals


@router.get("/summary", response_model=RemovalSummaryResponse)
def removal_summary(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_removal_summary(db, current_user.id)


@router.post("/recheck-stale", response_model=list[RemovalRequestResponse])
def recheck_stale_removals(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dispatch verification tasks for all stale removal requests."""
    from app.tasks.removal_task import verify_removal_task

    stale = get_stale_removals(db, current_user.id)
    for removal in stale:
        verify_removal_task.delay(str(removal.id))
    return stale


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
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removal = db.query(RemovalRequest).filter(
        RemovalRequest.id == removal_id,
        RemovalRequest.user_id == current_user.id,
    ).first()
    if not removal:
        raise HTTPException(status_code=404, detail="Removal request not found", headers={"code": "NOT_FOUND"})

    # Dispatch async verification via broker adapter
    from app.tasks.removal_task import verify_removal_task
    verify_removal_task.delay(str(removal.id))

    return removal
