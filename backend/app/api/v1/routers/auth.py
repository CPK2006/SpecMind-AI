from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database.dependencies import get_db
from app.models.user import User
from app.schemas.api_response import APIResponse
from app.schemas.auth import AuthToken, UserLogin, UserPublic, UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[AuthToken],
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    existing = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    token = create_access_token(str(user.id))
    return APIResponse(
        success=True,
        message="Account registered successfully.",
        data=AuthToken(
            access_token=token,
            user=UserPublic.model_validate(user),
        ),
    )


@router.post(
    "/login",
    response_model=APIResponse[AuthToken],
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )

    # Use the same response for an unknown email and a wrong password.
    if user is None or not verify_password(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Upgrade a legacy hash only after successful password verification.
    from app.core.security import is_legacy_password_hash

    if is_legacy_password_hash(user.hashed_password):
        user.hashed_password = hash_password(payload.password)
        db.commit()
        db.refresh(user)

    token = create_access_token(str(user.id))
    return APIResponse(
        success=True,
        message="Login successful.",
        data=AuthToken(
            access_token=token,
            user=UserPublic.model_validate(user),
        ),
    )
