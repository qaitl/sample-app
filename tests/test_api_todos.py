import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.repositories.memory import InMemoryTodoRepository
from src.services.todo_service import TodoService


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.state.service = TodoService(InMemoryTodoRepository())
    return TestClient(app)


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_endpoint(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"python_gc_objects_collected_total" in resp.content


def test_create_todo_json(client: TestClient) -> None:
    resp = client.post("/api/v1/todos", json={"title": "Hello"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Hello"
    assert not data["completed"]


def test_list_todos_json(client: TestClient) -> None:
    client.post("/api/v1/todos", json={"title": "T1"})
    client.post("/api/v1/todos", json={"title": "T2"})
    resp = client.get("/api/v1/todos")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_todo_json(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Fetch me"}).json()
    resp = client.get(f"/api/v1/todos/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_update_todo_json(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Old"}).json()
    resp = client.patch(f"/api/v1/todos/{created['id']}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_delete_todo_json(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Bye"}).json()
    resp = client.delete(f"/api/v1/todos/{created['id']}")
    assert resp.status_code == 204
    resp2 = client.get(f"/api/v1/todos/{created['id']}")
    assert resp2.status_code == 404


def test_complete_todo_htmx(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Check"}).json()
    resp = client.patch(f"/todos/{created['id']}/complete")
    assert resp.status_code == 200
    assert "todo-item--done" in resp.text


def test_delete_todo_htmx(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Remove"}).json()
    resp = client.delete(f"/todos/{created['id']}")
    assert resp.status_code == 200
    assert resp.text == ""


def test_index_page(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Todo App" in resp.text


def test_create_todo_htmx_form(client: TestClient) -> None:
    resp = client.post("/todos", data={"title": "Via form"})
    assert resp.status_code == 200
    assert "Via form" in resp.text


def test_404_on_unknown_todo(client: TestClient) -> None:
    from uuid import uuid4
    resp = client.get(f"/api/v1/todos/{uuid4()}")
    assert resp.status_code == 404
