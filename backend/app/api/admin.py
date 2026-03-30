import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.invite import InviteCode
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


@router.get("/brokers")
def list_brokers(admin: UserProfile = Depends(get_admin_user)):
    """Return all supported broker sites and their status."""
    return [
        {"slug": "spokeo", "display_name": "Spokeo", "status": "active"},
        {"slug": "whitepages", "display_name": "Whitepages", "status": "planned"},
        {"slug": "beenverified", "display_name": "BeenVerified", "status": "planned"},
        {"slug": "intelius", "display_name": "Intelius", "status": "planned"},
        {"slug": "peoplefinder", "display_name": "PeopleFinder", "status": "planned"},
        {"slug": "truepeoplesearch", "display_name": "TruePeopleSearch", "status": "planned"},
        {"slug": "fastpeoplesearch", "display_name": "FastPeopleSearch", "status": "planned"},
        {"slug": "thatsthem", "display_name": "ThatsThem", "status": "planned"},
        {"slug": "usphonebook", "display_name": "USPhonebook", "status": "planned"},
        {"slug": "voterrecords", "display_name": "VoterRecords", "status": "planned"},
        {"slug": "cyberbackgroundchecks", "display_name": "CyberBackgroundChecks", "status": "planned"},
        {"slug": "mylife", "display_name": "MyLife", "status": "planned"},
        {"slug": "radaris", "display_name": "Radaris", "status": "planned"},
        {"slug": "familytreenow", "display_name": "FamilyTreeNow", "status": "planned"},
        {"slug": "nuwber", "display_name": "Nuwber", "status": "planned"},
        {"slug": "clustrmaps", "display_name": "ClustrMaps", "status": "planned"},
        {"slug": "smartbackgroundchecks", "display_name": "SmartBackgroundChecks", "status": "planned"},
        {"slug": "addresses", "display_name": "Addresses.com", "status": "planned"},
        {"slug": "anywho", "display_name": "AnyWho", "status": "planned"},
        {"slug": "publicrecordsnow", "display_name": "PublicRecordsNow", "status": "planned"},
    ]
