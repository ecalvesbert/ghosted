import json
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from cryptography.fernet import Fernet

from app.config import get_settings


def _get_fernet() -> Fernet:
    key = get_settings().ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY env var is not set")
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    """Encrypt a plaintext string. Returns Fernet ciphertext as a UTF-8 string."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a Fernet ciphertext string. Returns plaintext."""
    return _get_fernet().decrypt(value.encode()).decode()


def encrypt_list(values: list[str]) -> str:
    """Encrypt a list of strings as JSON."""
    return encrypt(json.dumps(values))


def decrypt_list(value: str) -> list[str]:
    """Decrypt a Fernet ciphertext back to a list of strings."""
    if not value:
        return []
    return json.loads(decrypt(value))


@dataclass
class DecryptedProfile:
    """
    Ephemeral, in-memory only. Never persisted, never logged.
    Created by the scan engine from UserProfile, passed to adapters.
    Discarded after the scan completes.
    """
    id: UUID
    full_name: str
    phone_numbers: list[str]
    email_addresses: list[str]
    addresses: list[str]
    age_range: Optional[str]
    relatives: list[str]


def decrypt_profile(user) -> DecryptedProfile:
    """Decrypt a UserProfile ORM object into an ephemeral DecryptedProfile."""
    return DecryptedProfile(
        id=user.id,
        full_name=decrypt(user.full_name) if user.full_name else "",
        phone_numbers=decrypt_list(user.phone_numbers) if user.phone_numbers else [],
        email_addresses=decrypt_list(user.email_addresses) if user.email_addresses else [],
        addresses=decrypt_list(user.addresses) if user.addresses else [],
        age_range=decrypt(user.age_range) if user.age_range else None,
        relatives=decrypt_list(user.relatives) if user.relatives else [],
    )
