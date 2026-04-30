from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from app.config import Settings, get_settings
from app.db.models import User
from typing import Any, AsyncGenerator
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_app_settings() -> Settings:
    return get_settings()


def _get_state_value(request: Request, name: str) -> Any:
    value = getattr(request.app.state, name, None)

    if value is None:
        raise HTTPException(
            status_code=500,
            detail=f"Application dependency '{name}' is not initialized.",
        )

    return value


def get_ml_model(request: Request) -> Any:
    return _get_state_value(request, "model")


def get_embedder(request: Request) -> Any:
    return _get_state_value(request, "embedder")


def get_http_client(request: Request) -> Any:
    return _get_state_value(request, "http_client")


def get_llm_client(request: Request) -> Any:
    return _get_state_value(request, "llm_client")


def get_db_engine(request: Request) -> Any:
    return _get_state_value(request, "db_engine")


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_maker = _get_state_value(request, "session_maker")

    async with session_maker() as session:
        yield session
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_error

    except JWTError:
        raise credentials_error

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_error

    return user