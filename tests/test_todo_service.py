import pytest

from src.models.todo import TodoCreate, TodoUpdate
from src.repositories.memory import InMemoryTodoRepository
from src.services.todo_service import TodoService


@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository())


async def test_create_todo(service: TodoService) -> None:
    todo = await service.create_todo(TodoCreate(title="Test task"))
    assert todo.title == "Test task"
    assert not todo.completed


async def test_get_all(service: TodoService) -> None:
    await service.create_todo(TodoCreate(title="A"))
    await service.create_todo(TodoCreate(title="B"))
    todos = await service.get_all()
    assert len(todos) == 2


async def test_complete_todo(service: TodoService) -> None:
    todo = await service.create_todo(TodoCreate(title="Complete me"))
    completed = await service.complete_todo(todo.id)
    assert completed is not None
    assert completed.completed


async def test_complete_already_done(service: TodoService) -> None:
    todo = await service.create_todo(TodoCreate(title="Done"))
    await service.complete_todo(todo.id)
    result = await service.complete_todo(todo.id)
    assert result is None  # already completed — idempotent guard


async def test_delete_todo(service: TodoService) -> None:
    todo = await service.create_todo(TodoCreate(title="Delete me"))
    deleted = await service.delete_todo(todo.id)
    assert deleted
    assert await service.get_by_id(todo.id) is None


async def test_update_todo(service: TodoService) -> None:
    todo = await service.create_todo(TodoCreate(title="Old"))
    updated = await service.update_todo(todo.id, TodoUpdate(title="New"))
    assert updated is not None
    assert updated.title == "New"


async def test_sync_active_gauge(service: TodoService) -> None:
    await service.create_todo(TodoCreate(title="A"))
    await service.create_todo(TodoCreate(title="B"))
    # Just ensure it runs without error
    await service.sync_active_gauge()
