# sample-app — Todo List + Monitoring Demo

Application de démonstration Python 3.13 illustrant l'intégration d'une stack d'observabilité
Prometheus / Grafana / Loki sur une API FastAPI avec frontend HTMX.

## Démarrage rapide

```bash
# Installer les dépendances
uv sync

# Lancer l'application (mode dev)
uv run uvicorn src.main:app --reload
```

Ouvrir `http://localhost:8000`.

## Avec monitoring complet

```bash
# 1. Démarrer l'application conteneurisée
docker compose up -d --build

# 2. Démarrer la stack monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

| Service | URL | Identifiants |
|---|---|---|
| Application | http://localhost:8000 | — |
| Métriques | http://localhost:8000/metrics | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

Le dashboard **Todo App** est pré-provisionné dans Grafana.

## Tests

```bash
uv run pytest tests/ -v
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — Choix architecturaux, cycle de vie d'une requête
- [docs/monitoring.md](docs/monitoring.md) — Métriques, logs, dashboard Grafana
- [docs/repository-pattern.md](docs/repository-pattern.md) — Migration vers SQLite / PostgreSQL
- [docs/configuration.md](docs/configuration.md) — Référence `config.yaml` et variables d'env
- [docs/development.md](docs/development.md) — Setup local, commandes uv

## Stack technique

- **Runtime** : Python 3.13, [uv](https://docs.astral.sh/uv/)
- **API** : FastAPI + uvicorn
- **Frontend** : HTMX 2 + Jinja2 (pas de build JS)
- **Configuration** : YAML + pydantic-settings (surcharge par env vars)
- **Métriques** : prometheus-fastapi-instrumentator + métriques custom
- **Logs** : structlog (JSON) → Promtail → Loki
- **Dashboards** : Grafana avec provisionnement automatique
