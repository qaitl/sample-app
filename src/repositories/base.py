from abc import ABC, abstractmethod
from uuid import UUID

from src.models.todo import TodoCreate, TodoInDB, TodoUpdate


class AbstractTodoRepository(ABC):
    """Contract that every storage backend must satisfy.

    All methods are async so that concrete implementations can use
    async I/O (aiosqlite, asyncpg, etc.) without changing callers.
    """

    @abstractmethod
    async def get_all(self) -> list[TodoInDB]: ...

    @abstractmethod
    async def get_by_id(self, todo_id: UUID) -> TodoInDB | None: ...

    @abstractmethod
    async def create(self, data: TodoCreate) -> TodoInDB: ...

    @abstractmethod
    async def update(self, todo_id: UUID, data: TodoUpdate) -> TodoInDB | None: ...

    @abstractmethod
    async def delete(self, todo_id: UUID) -> bool: ...

    @abstractmethod
    async def count_active(self) -> int: ...
