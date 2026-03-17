from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.models.todo import TodoCreate, TodoResponse, TodoUpdate
from src.services.todo_service import TodoService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = structlog.get_logger(__name__)


def get_service(request: Request) -> TodoService:
    return request.app.state.service  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# HTMX endpoints — return HTML fragments
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    service: TodoService = Depends(get_service),
) -> HTMLResponse:
    todos = await service.get_all()
    return templates.TemplateResponse(request, "index.html", {"todos": todos})


@router.post("/todos", response_class=HTMLResponse)
async def create_todo_htmx(
    request: Request,
    title: str = Form(...),
    description: str | None = Form(default=None),
    service: TodoService = Depends(get_service),
) -> HTMLResponse:
    todo = await service.create_todo(TodoCreate(title=title, description=description))
    logger.info("todo_created", todo_id=str(todo.id), title=title)
    todos = await service.get_all()
    return templates.TemplateResponse(
        request, "partials/todo_list.html", {"todos": todos}
    )


@router.patch("/todos/{todo_id}/complete", response_class=HTMLResponse)
async def complete_todo_htmx(
    todo_id: UUID,
    request: Request,
    service: TodoService = Depends(get_service),
) -> HTMLResponse:
    todo = await service.complete_todo(todo_id)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    logger.info("todo_completed", todo_id=str(todo_id))
    return templates.TemplateResponse(
        request, "partials/todo_item.html", {"todo": todo}
    )


@router.delete("/todos/{todo_id}", response_class=HTMLResponse)
async def delete_todo_htmx(
    todo_id: UUID,
    request: Request,
    service: TodoService = Depends(get_service),
) -> HTMLResponse:
    deleted = await service.delete_todo(todo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    logger.info("todo_deleted", todo_id=str(todo_id))
    return HTMLResponse(content="", status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# JSON endpoints — for curl / external consumers / tests
# ---------------------------------------------------------------------------


@router.get("/api/v1/todos", response_model=list[TodoResponse])
async def list_todos_json(
    service: TodoService = Depends(get_service),
) -> list[TodoResponse]:
    return await service.get_all()


@router.post(
    "/api/v1/todos",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_todo_json(
    data: TodoCreate,
    service: TodoService = Depends(get_service),
) -> TodoResponse:
    return await service.create_todo(data)


@router.get("/api/v1/todos/{todo_id}", response_model=TodoResponse)
async def get_todo_json(
    todo_id: UUID,
    service: TodoService = Depends(get_service),
) -> TodoResponse:
    todo = await service.get_by_id(todo_id)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    return todo


@router.patch("/api/v1/todos/{todo_id}", response_model=TodoResponse)
async def update_todo_json(
    todo_id: UUID,
    data: TodoUpdate,
    service: TodoService = Depends(get_service),
) -> TodoResponse:
    todo = await service.update_todo(todo_id, data)
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    return todo


@router.delete("/api/v1/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_json(
    todo_id: UUID,
    service: TodoService = Depends(get_service),
) -> None:
    deleted = await service.delete_todo(todo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
