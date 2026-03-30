import os
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.invite import InviteCode
from app.models.scan import ScanJob
from app.services.encryption import decrypt_profile
from app.schemas.auth import BootstrapRequest
from app.schemas.invite import InviteCreateRequest, InviteCodeResponse
from app.services.auth import hash_password, create_token, get_admin_user
from app.services.encryption import encrypt
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/bootstrap")
def bootstrap(req: BootstrapRequest, db: Session = Depends(get_db)):
    settings = get_settings()

    # Self-disabling: if any admin exists, return 410
    existing_admin = db.query(UserProfile).filter(UserProfile.is_admin == True).first()
    if existing_admin:
        raise HTTPException(
            status_code=410,
            detail="Bootstrap already completed",
            headers={"code": "BOOTSTRAP_ALREADY_DONE"},
        )

    # Verify admin secret
    if not settings.ADMIN_BOOTSTRAP_SECRET or req.admin_secret != settings.ADMIN_BOOTSTRAP_SECRET:
        raise HTTPException(status_code=401, detail="Invalid admin secret", headers={"code": "UNAUTHORIZED"})

    user = UserProfile(
        email=encrypt(req.email),
        hashed_password=hash_password(req.password),
        invite_code_used="__bootstrap__",
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, is_admin=True)
    return {"token": token}


def _generate_code(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@router.post("/invites", response_model=InviteCodeResponse, status_code=201)
def create_invite(
    req: InviteCreateRequest,
    admin: UserProfile = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    code = _generate_code()
    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)

    invite = InviteCode(
        code=code,
        created_by=admin.id,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/invites", response_model=list[InviteCodeResponse])
def list_invites(
    admin: UserProfile = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return db.query(InviteCode).all()


@router.post("/scans/{scan_id}/cancel")
def cancel_scan(
    scan_id: str,
    admin: UserProfile = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    scan = db.query(ScanJob).filter(ScanJob.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found", headers={"code": "NOT_FOUND"})
    scan.status = "failed"
    scan.error = "Cancelled by admin"
    scan.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "cancelled"}


@router.post("/debug/browserbase")
def debug_browserbase(
    admin: UserProfile = Depends(get_admin_user),
):
    """Create a Browserbase session and return the live view URL for debugging."""
    from browserbase import Browserbase

    api_key = os.getenv("BROWSERBASE_API_KEY")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")
    if not api_key or not project_id:
        raise HTTPException(status_code=500, detail="Browserbase not configured")

    bb = Browserbase(api_key=api_key)
    session = bb.sessions.create(project_id=project_id)

    # Build Spokeo search URL from admin's profile
    profile = decrypt_profile(admin)
    location = ""
    if profile.city and profile.state:
        location = f", {profile.city}, {profile.state}"
    search_url = f"https://www.spokeo.com/search?q={profile.full_name.replace(' ', '+')}{location.replace(' ', '+').replace(',', '%2C')}"

    return {
        "session_id": session.id,
        "connect_url": session.connect_url,
        "live_view": f"https://www.browserbase.com/sessions/{session.id}",
        "spokeo_search_url": search_url,
    }


@router.get("/brokers")
def list_brokers(admin: UserProfile = Depends(get_admin_user)):
    # Return registered broker adapters and their status
    # Placeholder — populated when broker adapters are built in Phase 2
    return [
        {"slug": "spokeo", "display_name": "Spokeo", "status": "active"},
        {"slug": "whitepages", "display_name": "Whitepages", "status": "active"},
        {"slug": "beenverified", "display_name": "BeenVerified", "status": "active"},
        {"slug": "intelius", "display_name": "Intelius", "status": "active"},
        {"slug": "peoplefinder", "display_name": "PeopleFinder", "status": "active"},
    ]
