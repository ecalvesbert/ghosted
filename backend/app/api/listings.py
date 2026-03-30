from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.listing import FoundListing
from app.models.removal import RemovalRequest
from app.schemas.listing import FoundListingResponse, ListingUpdateRequest
from app.schemas.removal import RemovalRequestResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.patch("/{listing_id}", response_model=FoundListingResponse)
def update_listing(
    listing_id: str,
    req: ListingUpdateRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.status not in ("approved", "skipped"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'skipped'", headers={"code": "INVALID_STATUS"})

    listing = db.query(FoundListing).filter(
        FoundListing.id == listing_id,
        FoundListing.user_id == current_user.id,
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found", headers={"code": "NOT_FOUND"})

    listing.status = req.status
    listing.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/{listing_id}/remove", response_model=RemovalRequestResponse, status_code=201)
def remove_listing(
    listing_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(FoundListing).filter(
        FoundListing.id == listing_id,
        FoundListing.user_id == current_user.id,
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found", headers={"code": "NOT_FOUND"})

    if listing.status != "approved":
        raise HTTPException(status_code=400, detail="Listing must be approved before removal", headers={"code": "INVALID_STATUS"})

    removal = RemovalRequest(
        listing_id=listing.id,
        user_id=current_user.id,
        broker=listing.broker,
        method=listing.removal_method or "automated",
        status="removal_sent",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(removal)

    listing.status = "removal_sent"
    listing.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(removal)

    # Dispatch async removal via broker adapter
    from app.tasks.removal_task import submit_removal_task
    submit_removal_task.delay(str(listing.id))

    return removal
