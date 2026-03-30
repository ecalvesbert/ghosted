from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.models.invite import InviteCode
from app.schemas.auth import RegisterRequest, TokenRequest, TokenResponse
from app.schemas.profile import UserPublic
from app.services.auth import hash_password, verify_password, create_token, get_current_user
from app.services.encryption import encrypt, decrypt

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Validate invite code — lock row to prevent concurrent use
    invite = db.query(InviteCode).filter(InviteCode.code == req.invite_code).with_for_update().first()
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code", headers={"code": "INVALID_INVITE"})
    if invite.is_used:
        raise HTTPException(status_code=400, detail="Invite code already used", headers={"code": "INVALID_INVITE"})
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite code expired", headers={"code": "INVALID_INVITE"})

    # Check email uniqueness — need to check all encrypted emails
    existing_users = db.query(UserProfile).all()
    for u in existing_users:
        try:
            if decrypt(u.email) == req.email:
                raise HTTPException(status_code=400, detail="Email already registered", headers={"code": "INVALID_INVITE"})
        except HTTPException:
            raise
        except Exception:
            continue

    user = UserProfile(
        email=encrypt(req.email),
        hashed_password=hash_password(req.password),
        invite_code_used=req.invite_code,
    )
    db.add(user)

    # Mark invite as used
    invite.is_used = True
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return {
        "token": token,
        "user": UserPublic(
            id=user.id,
            email=req.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    }


@router.post("/token", response_model=TokenResponse)
def login(req: TokenRequest, db: Session = Depends(get_db)):
    users = db.query(UserProfile).all()
    for user in users:
        try:
            if decrypt(user.email) == req.email:
                if verify_password(req.password, user.hashed_password):
                    token = create_token(user.id, is_admin=user.is_admin)
                    return TokenResponse(token=token)
                raise HTTPException(status_code=401, detail="Invalid credentials", headers={"code": "UNAUTHORIZED"})
        except HTTPException:
            raise
        except Exception:
            continue
    raise HTTPException(status_code=401, detail="Invalid credentials", headers={"code": "UNAUTHORIZED"})


@router.get("/me")
def me(current_user: UserProfile = Depends(get_current_user)):
    return UserPublic(
        id=current_user.id,
        email=decrypt(current_user.email),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
