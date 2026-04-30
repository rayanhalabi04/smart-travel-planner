from sqlalchemy.orm import DeclarativeBase

from app.db.models import Base

__all__ = ["Base"]
class Base(DeclarativeBase):
    pass