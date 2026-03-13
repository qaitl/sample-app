# Pattern Repository — Guide de migration

## Principe

Le `AbstractTodoRepository` (`src/repositories/base.py`) définit le contrat que tout backend de
stockage doit respecter. Les routes et le service n'ont connaissance que de cette interface, jamais
d'une implémentation concrète.

```python
class AbstractTodoRepository(ABC):
    async def get_all(self) -> list[TodoInDB]: ...
    async def get_by_id(self, todo_id: UUID) -> TodoInDB | None: ...
    async def create(self, data: TodoCreate) -> TodoInDB: ...
    async def update(self, todo_id: UUID, data: TodoUpdate) -> TodoInDB | None: ...
    async def delete(self, todo_id: UUID) -> bool: ...
    async def count_active(self) -> int: ...
```

Toutes les méthodes sont `async` dès le départ pour que les implémentations I/O-bound
(SQLite async, asyncpg) n'imposent aucun changement aux callers.

## Migration vers SQLite

### 1. Ajouter la dépendance

```bash
uv add aiosqlite
```

### 2. Créer `src/repositories/sqlite.py`

```python
import aiosqlite
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.repositories.base import AbstractTodoRepository
from src.models.todo import TodoCreate, TodoInDB, TodoUpdate

class SQLiteTodoRepository(AbstractTodoRepository):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def _ensure_table(self, conn: aiosqlite.Connection) -> None:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await conn.commit()

    async def create(self, data: TodoCreate) -> TodoInDB:
        now = datetime.now(tz=timezone.utc)
        todo = TodoInDB(
            id=uuid4(), title=data.title, description=data.description,
            completed=False, created_at=now, updated_at=now
        )
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_table(db)
            await db.execute(
                "INSERT INTO todos VALUES (?, ?, ?, ?, ?, ?)",
                (str(todo.id), todo.title, todo.description, 0,
                 todo.created_at.isoformat(), todo.updated_at.isoformat())
            )
            await db.commit()
        return todo

    # ... implémenter les autres méthodes de la même façon
    async def count_active(self) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            await self._ensure_table(db)
            cursor = await db.execute("SELECT COUNT(*) FROM todos WHERE completed=0")
            row = await cursor.fetchone()
            return row[0] if row else 0
```

### 3. Mettre à jour `config.yaml`

```yaml
storage:
  backend: "sqlite"
  sqlite_path: "./todos.db"
```

C'est tout — `main.py` sélectionne automatiquement l'implémentation via le `match`.

## Migration vers PostgreSQL

### 1. Ajouter les dépendances

```bash
uv add sqlalchemy[asyncio] asyncpg
```

### 2. Créer `src/repositories/postgresql.py`

Utilise SQLAlchemy async avec un modèle ORM ou des requêtes Core :

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class PostgreSQLTodoRepository(AbstractTodoRepository):
    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
    # ... implémenter les méthodes avec AsyncSession
```

### 3. Mettre à jour `config.yaml`

```yaml
storage:
  backend: "postgresql"
  database_url: "postgresql+asyncpg://user:password@localhost:5432/todos"
```

## Sélection du backend dans `main.py`

```python
def _build_repository(settings: Settings) -> AbstractTodoRepository:
    match settings.storage.backend:
        case "memory":
            return InMemoryTodoRepository()
        case "sqlite":
            from src.repositories.sqlite import SQLiteTodoRepository
            return SQLiteTodoRepository(settings.storage.sqlite_path)
        case "postgresql":
            from src.repositories.postgresql import PostgreSQLTodoRepository
            return PostgreSQLTodoRepository(settings.storage.database_url)
        case _:
            raise ValueError(f"Unknown backend: {settings.storage.backend}")
```

## Stratégie de tests

Le pattern Repository permet de tester le service sans base de données réelle :

```python
# tests/conftest.py
@pytest.fixture
def service() -> TodoService:
    return TodoService(InMemoryTodoRepository())  # zéro I/O
```

Pour tester un nouveau backend, créer un fichier `tests/test_repository_sqlite.py` qui utilise
une base en mémoire SQLite (`:memory:`) ou un fichier temporaire.
