from datetime import datetime
from typing import Annotated
from sqlalchemy import create_engine
from src.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker
from sqlalchemy import String, create_engine, text

sync_engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
    echo=True,
)
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=True,
)

session_factory = sessionmaker(sync_engine)
async_session_factory = async_sessionmaker(async_engine)

str_256 = Annotated[str, 256]
float_nullable = Annotated[float, mapped_column(nullable=True)]
datetime_now = Annotated[datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]

class Base(DeclarativeBase):
    type_annotation_map = {
        str_256: String(256)
    }
    def __repr__(self):
        cols = [f"{col}={getattr(self, col)}" for col in self.__table__.columns.keys()[:3]]
        return f"<{self.__class__.__name__} {','.join(cols)}>"
