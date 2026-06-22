from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


def register_user(db: Session, email: str, password: str, full_name: str) -> Optional[User]:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None  # caller checks for None → 409
    user = User(email=email, password_hash=hash_password(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_token_for_user(db: Session, email: str, password: str) -> Optional[str]:
    user = authenticate_user(db, email, password)
    if not user:
        return None
    return create_access_token(user.id)
