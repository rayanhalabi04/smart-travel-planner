from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_app_settings, get_current_user, get_db_session
from app.config import Settings
from app.db.models import User
from app.dependencies import get_app_settings, get_db_session
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    get_user_by_email,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    existing_user = await get_user_by_email(session, payload.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    user = await get_user_by_email(session, payload.email)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user.id, settings)

    return TokenResponse(access_token=token)
@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)