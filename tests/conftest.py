import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.repositories.memory import InMemoryTodoRepository
from src.services.todo_service import TodoService


@pytest.fixture
def repo() -> InMemoryTodoRepository:
    return InMemoryTodoRepository()


@pytest.fixture
def service(repo: InMemoryTodoRepository) -> TodoService:
    return TodoService(repo)


@pytest.fixture
def client(service: TodoService) -> TestClient:
    app = create_app()
    app.state.service = service
    return TestClient(app)
