from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None


class TodoInDB(BaseModel):
    id: UUID
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime


class TodoResponse(TodoInDB):
    pass
