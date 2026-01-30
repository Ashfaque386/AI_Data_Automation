"""
Authentication Service
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, RefreshToken
from app.schemas import Token, TokenPayload


def create_access_token(user: User) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user: User, db: Session) -> str:
    """Create JWT refresh token and store in database."""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expire,
        "type": "refresh"
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Store refresh token
    db_token = RefreshToken(
        user_id=user.id,
        token=token,
        expires_at=expire
    )
    db.add(db_token)
    db.commit()
    
    return token


def create_tokens(user: User, db: Session) -> Token:
    """Create both access and refresh tokens."""
    return Token(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user, db),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return TokenPayload(
            sub=int(payload["sub"]),
            email=payload["email"],
            exp=datetime.fromtimestamp(payload["exp"]),
            type=payload["type"]
        )
    except JWTError:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.verify_password(password):
        return None
    if not user.is_active:
        return None
    return user


def refresh_access_token(db: Session, refresh_token: str) -> Optional[Token]:
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        return None
    
    # Check if token is in database and not revoked
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.revoked == False
    ).first()
    
    if not db_token or db_token.expires_at < datetime.utcnow():
        return None
    
    # Get user
    user = db.query(User).filter(User.id == payload.sub).first()
    if not user or not user.is_active:
        return None
    
    # Revoke old refresh token
    db_token.revoked = True
    db.commit()
    
    # Create new tokens
    return create_tokens(user, db)


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Revoke a refresh token."""
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
        return True
    return False


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()
