import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.models.todo import TodoCreate, TodoInDB, TodoUpdate
from src.repositories.base import AbstractTodoRepository


class InMemoryTodoRepository(AbstractTodoRepository):
    """Thread-safe in-memory store backed by a plain dict.

    Data is lost on process restart — use this for development and demos.
    To persist data, implement a concrete repository for SQLite or PostgreSQL
    (see docs/repository-pattern.md).
    """

    def __init__(self) -> None:
        self._store: dict[UUID, TodoInDB] = {}
        self._lock = asyncio.Lock()

    async def get_all(self) -> list[TodoInDB]:
        async with self._lock:
            return list(self._store.values())

    async def get_by_id(self, todo_id: UUID) -> TodoInDB | None:
        async with self._lock:
            return self._store.get(todo_id)

    async def create(self, data: TodoCreate) -> TodoInDB:
        now = datetime.now(tz=UTC)
        todo = TodoInDB(
            id=uuid4(),
            title=data.title,
            description=data.description,
            completed=False,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._store[todo.id] = todo
        return todo

    async def update(self, todo_id: UUID, data: TodoUpdate) -> TodoInDB | None:
        async with self._lock:
            existing = self._store.get(todo_id)
            if existing is None:
                return None
            updated = existing.model_copy(
                update={
                    k: v
                    for k, v in data.model_dump(exclude_none=True).items()
                    if v is not None
                }
                | {"updated_at": datetime.now(tz=UTC)},
            )
            self._store[todo_id] = updated
            return updated

    async def delete(self, todo_id: UUID) -> bool:
        async with self._lock:
            if todo_id not in self._store:
                return False
            del self._store[todo_id]
            return True

    async def count_active(self) -> int:
        async with self._lock:
            return sum(1 for t in self._store.values() if not t.completed)
