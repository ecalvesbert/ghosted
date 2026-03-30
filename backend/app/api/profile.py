from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserProfile
from app.schemas.profile import UserProfilePublic, UserProfileUpdate
from app.services.auth import get_current_user
from app.services.encryption import decrypt, decrypt_list, encrypt, encrypt_list

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _to_public(user: UserProfile) -> UserProfilePublic:
    return UserProfilePublic(
        id=user.id,
        email=decrypt(user.email),
        full_name=decrypt(user.full_name) if user.full_name else "",
        phone_numbers=decrypt_list(user.phone_numbers) if user.phone_numbers else [],
        email_addresses=decrypt_list(user.email_addresses) if user.email_addresses else [],
        addresses=decrypt_list(user.addresses) if user.addresses else [],
        age_range=decrypt(user.age_range) if user.age_range else None,
        relatives=decrypt_list(user.relatives) if user.relatives else [],
        telegram_chat_id=user.telegram_chat_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=UserProfilePublic)
def get_profile(current_user: UserProfile = Depends(get_current_user)):
    return _to_public(current_user)


@router.put("", response_model=UserProfilePublic)
def update_profile(
    update: UserProfileUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if update.full_name is not None:
        current_user.full_name = encrypt(update.full_name)
    if update.phone_numbers is not None:
        current_user.phone_numbers = encrypt_list(update.phone_numbers)
    if update.email_addresses is not None:
        current_user.email_addresses = encrypt_list(update.email_addresses)
    if update.addresses is not None:
        current_user.addresses = encrypt_list(update.addresses)
    if update.age_range is not None:
        current_user.age_range = encrypt(update.age_range)
    if update.relatives is not None:
        current_user.relatives = encrypt_list(update.relatives)
    if update.telegram_chat_id is not None:
        current_user.telegram_chat_id = update.telegram_chat_id

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return _to_public(current_user)
