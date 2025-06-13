from typing import Annotated
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.queries.databaseORM import session_factory

class PaginationParams(BaseModel):
    limit: int = Field(5, ge=0, le=100, description="Кол-во элементов на странице")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    
SessionDep = Annotated[AsyncSession, Depends(session_factory)]

PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]