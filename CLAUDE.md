# CLAUDE.md — Contexte projet pour Claude Code

## Vue d'ensemble

Application de démonstration d'une todo list Python 3.13 + uv + FastAPI, dont l'objectif
principal est de servir de référence pour une stack de monitoring Prometheus / Grafana / Loki.

## Commandes essentielles

```bash
# Développement
uv run uvicorn src.main:app --reload      # serveur dev (port 8000)
uv run pytest tests/ -v                   # tests
uv run ruff check src/ tests/             # lint
uv run mypy src/                          # types

# Docker
docker compose up --build                 # app seule
docker compose -f docker-compose.monitoring.yml up -d  # stack monitoring
```

## Architecture

- **FastAPI** + **HTMX** + **Jinja2** (pas de SPA, pas de build JS)
- **Pattern Repository** : `AbstractTodoRepository` → `InMemoryTodoRepository`
- **Métriques** : `prometheus-fastapi-instrumentator` (auto HTTP) + 3 métriques custom dans `todo_service.py`
- **Logs** : `structlog` → JSON stdout → Promtail → Loki

## Fichiers clés

| Fichier | Rôle |
|---|---|
| [src/main.py](src/main.py) | Factory FastAPI, lifespan, middleware request_id |
| [src/config.py](src/config.py) | Pydantic Settings + source YAML custom |
| [src/repositories/base.py](src/repositories/base.py) | ABC du repository |
| [src/repositories/memory.py](src/repositories/memory.py) | Implémentation en mémoire |
| [src/services/todo_service.py](src/services/todo_service.py) | Logique métier + métriques custom |
| [src/api/v1/todos.py](src/api/v1/todos.py) | Routes HTMX et JSON |
| [config.yaml](config.yaml) | Configuration par défaut |

## Variables d'environnement

Préfixe `APP_`, séparateur `__`. Exemple : `APP_APP__LOG_LEVEL=DEBUG`.
Voir [docs/configuration.md](docs/configuration.md) pour la référence complète.

## Étendre le stockage

Implémenter `AbstractTodoRepository`, changer `storage.backend` dans `config.yaml`.
Voir [docs/repository-pattern.md](docs/repository-pattern.md).

## Stack monitoring

- Prometheus : `http://localhost:9090` — cible `sample-app:8000/metrics`
- Grafana : `http://localhost:3000` — admin/admin — dashboard "Todo App" pré-provisionné
- Loki : logs JSON de l'app collectés par Promtail

## Conventions

- Async partout dans les repositories et services
- Métriques Prometheus uniquement dans `todo_service.py`
- Logs structurés via `structlog.get_logger(__name__)`
- Tests avec `InMemoryTodoRepository` (zéro I/O)
