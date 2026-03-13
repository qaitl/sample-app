from uuid import UUID

from prometheus_client import Counter, Gauge

from src.models.todo import TodoCreate, TodoInDB, TodoResponse, TodoUpdate
from src.repositories.base import AbstractTodoRepository

# Custom Prometheus metrics — the service is the sole place that touches them.
todos_created_total = Counter(
    "todos_created_total",
    "Total number of todo items created",
)
todos_completed_total = Counter(
    "todos_completed_total",
    "Total number of todo items marked as completed",
)
todos_active = Gauge(
    "todos_active",
    "Current number of active (incomplete) todo items",
)


class TodoService:
    def __init__(self, repo: AbstractTodoRepository) -> None:
        self.repo = repo

    async def get_all(self) -> list[TodoResponse]:
        todos = await self.repo.get_all()
        return [TodoResponse.model_validate(t.model_dump()) for t in todos]

    async def get_by_id(self, todo_id: UUID) -> TodoResponse | None:
        todo = await self.repo.get_by_id(todo_id)
        if todo is None:
            return None
        return TodoResponse.model_validate(todo.model_dump())

    async def create_todo(self, data: TodoCreate) -> TodoResponse:
        todo = await self.repo.create(data)
        todos_created_total.inc()
        todos_active.inc()
        return TodoResponse.model_validate(todo.model_dump())

    async def update_todo(self, todo_id: UUID, data: TodoUpdate) -> TodoResponse | None:
        existing = await self.repo.get_by_id(todo_id)
        if existing is None:
            return None
        was_completed = existing.completed
        todo = await self.repo.update(todo_id, data)
        if todo is None:
            return None
        # Track completion transitions
        if not was_completed and todo.completed:
            todos_completed_total.inc()
            todos_active.dec()
        elif was_completed and not todo.completed:
            todos_active.inc()
        return TodoResponse.model_validate(todo.model_dump())

    async def delete_todo(self, todo_id: UUID) -> bool:
        existing = await self.repo.get_by_id(todo_id)
        if existing is None:
            return False
        deleted = await self.repo.delete(todo_id)
        if deleted and not existing.completed:
            todos_active.dec()
        return deleted

    async def sync_active_gauge(self) -> None:
        """Sync the gauge with actual repository state at startup.

        Critical when migrating to a persistent backend: ensures the gauge
        reflects reality after a process restart rather than starting at 0.
        """
        count = await self.repo.count_active()
        todos_active.set(count)

    async def complete_todo(self, todo_id: UUID) -> TodoResponse | None:
        todo = await self.repo.get_by_id(todo_id)
        if todo is None or todo.completed:
            return None
        return await self.update_todo(todo_id, TodoUpdate(completed=True))

    async def get_todo_in_db(self, todo_id: UUID) -> TodoInDB | None:
        return await self.repo.get_by_id(todo_id)
