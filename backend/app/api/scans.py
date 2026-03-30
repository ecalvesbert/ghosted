from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.scan import ScanJob
from app.models.listing import FoundListing
from app.schemas.scan import ScanCreateRequest, ScanJobResponse
from app.schemas.listing import FoundListingResponse
from app.services.auth import get_current_user
from app.tasks.scan_task import run_scan

router = APIRouter(prefix="/api/scans", tags=["scans"])

DEFAULT_BROKERS = ["spokeo"]


@router.post("", response_model=ScanJobResponse, status_code=201)
def create_scan(
    req: ScanCreateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Enforce 1 active scan per user — lock rows to prevent race condition
    active = db.query(ScanJob).filter(
        ScanJob.user_id == current_user.id,
        ScanJob.status.in_(["pending", "running"]),
    ).with_for_update().first()
    if active:
        return JSONResponse(
            status_code=409,
            content={"detail": "A scan is already running", "code": "SCAN_ALREADY_RUNNING"},
        )

    brokers = req.brokers or DEFAULT_BROKERS
    scan = ScanJob(
        user_id=current_user.id,
        status="pending",
        brokers_targeted=brokers,
        brokers_completed=[],
        brokers_failed=[],
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Dispatch Celery task
    run_scan.delay(str(scan.id), str(current_user.id), brokers)

    return scan


@router.get("", response_model=list[ScanJobResponse])
def list_scans(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scans = db.query(ScanJob).filter(ScanJob.user_id == current_user.id).order_by(ScanJob.created_at.desc()).all()
    return scans


@router.get("/{scan_id}", response_model=ScanJobResponse)
def get_scan(
    scan_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(ScanJob).filter(ScanJob.id == scan_id, ScanJob.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found", headers={"code": "NOT_FOUND"})
    return scan


@router.get("/{scan_id}/listings", response_model=list[FoundListingResponse])
def get_scan_listings(
    scan_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = db.query(ScanJob).filter(ScanJob.id == scan_id, ScanJob.user_id == current_user.id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found", headers={"code": "NOT_FOUND"})
    listings = db.query(FoundListing).filter(
        FoundListing.scan_job_id == scan_id,
        FoundListing.user_id == current_user.id,
    ).order_by(FoundListing.priority.desc()).all()
    return listings
