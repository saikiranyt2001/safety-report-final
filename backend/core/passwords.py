import hashlib

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, stored_hash: str | None) -> tuple[bool, str | None]:
    if not stored_hash:
        return False, None

    if stored_hash.startswith("$pbkdf2-sha256$"):
        is_valid = pwd_context.verify(password, stored_hash)
        upgraded_hash = hash_password(password) if is_valid and pwd_context.needs_update(stored_hash) else None
        return is_valid, upgraded_hash

    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
    if legacy_hash == stored_hash:
        return True, hash_password(password)

    return False, None
