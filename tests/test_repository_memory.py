import pytest

from src.models.todo import TodoCreate, TodoUpdate
from src.repositories.memory import InMemoryTodoRepository


@pytest.fixture
def repo() -> InMemoryTodoRepository:
    return InMemoryTodoRepository()


async def test_create_and_get(repo: InMemoryTodoRepository) -> None:
    todo = await repo.create(TodoCreate(title="Buy milk"))
    assert todo.title == "Buy milk"
    assert not todo.completed

    fetched = await repo.get_by_id(todo.id)
    assert fetched is not None
    assert fetched.id == todo.id


async def test_get_all(repo: InMemoryTodoRepository) -> None:
    await repo.create(TodoCreate(title="Task 1"))
    await repo.create(TodoCreate(title="Task 2"))
    all_todos = await repo.get_all()
    assert len(all_todos) == 2


async def test_update(repo: InMemoryTodoRepository) -> None:
    todo = await repo.create(TodoCreate(title="Original"))
    updated = await repo.update(todo.id, TodoUpdate(title="Updated", completed=True))
    assert updated is not None
    assert updated.title == "Updated"
    assert updated.completed


async def test_delete(repo: InMemoryTodoRepository) -> None:
    todo = await repo.create(TodoCreate(title="To delete"))
    deleted = await repo.delete(todo.id)
    assert deleted
    assert await repo.get_by_id(todo.id) is None


async def test_delete_nonexistent(repo: InMemoryTodoRepository) -> None:
    from uuid import uuid4
    assert not await repo.delete(uuid4())


async def test_count_active(repo: InMemoryTodoRepository) -> None:
    t1 = await repo.create(TodoCreate(title="Active"))
    t2 = await repo.create(TodoCreate(title="Done"))
    await repo.update(t2.id, TodoUpdate(completed=True))
    assert await repo.count_active() == 1
    await repo.update(t1.id, TodoUpdate(completed=True))
    assert await repo.count_active() == 0
