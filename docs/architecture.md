# Architecture

## Vue d'ensemble

Cette application est une todo list de démonstration dont l'objectif premier est de servir de
référence pour une stack de monitoring Prometheus / Grafana / Loki. Le code métier est
intentionnellement simple afin de mettre l'accent sur l'observabilité.

## Choix technologiques

### FastAPI

FastAPI a été retenu pour :
- Sa génération automatique de documentation OpenAPI (`/docs`)
- Son système de dépendances (`Depends`) qui facilite l'injection du service dans les routes
- Le support natif des réponses asynchrones, cohérent avec le pattern Repository `async`
- Sa légèreté comparée à Django, adaptée à un projet de démo

### HTMX + Jinja2

HTMX permet des interactions dynamiques (ajout, complétion, suppression de tâches) sans étape de
build JavaScript ni framework SPA. La stack reste :
- **Backend** : FastAPI renvoie des fragments HTML (partials Jinja2) en réponse aux actions HTMX
- **Frontend** : un fichier CSS et HTMX vendorisé — zéro dépendance npm

Ce choix simplifie le projet et garde le focus sur le monitoring.

### Architecture en couches

```
HTTP Request
     │
     ▼
┌─────────────┐
│  API Routes │  src/api/v1/todos.py
│  (FastAPI)  │  — routing, validation HTTP, sérialisation
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  src/services/todo_service.py
│   Layer     │  — logique métier, émission des métriques Prometheus
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Repository │  src/repositories/base.py (ABC)
│  (abstract) │  src/repositories/memory.py (impl. mémoire)
└─────────────┘
```

**Règle stricte** : chaque couche ne connaît que la couche immédiatement en dessous.
Le service ne connaît pas FastAPI. Les routes ne connaissent pas les repositories.

### Modèles Pydantic

Quatre classes distinctes pour les todos :

| Classe | Usage |
|---|---|
| `TodoCreate` | Corps d'une requête POST |
| `TodoUpdate` | Corps d'une requête PATCH (champs optionnels) |
| `TodoInDB` | Représentation interne stockée dans le repository |
| `TodoResponse` | Forme publique renvoyée par l'API |

`TodoInDB` et `TodoResponse` sont identiques aujourd'hui mais découpés pour permettre d'ajouter
des champs internes (ex. `user_id`) sans les exposer dans l'API.

## Cycle de vie d'une requête

1. La requête arrive sur uvicorn → Starlette middleware (request_id)
2. prometheus-fastapi-instrumentator enregistre la durée et incrémente ses compteurs HTTP
3. Le routeur FastAPI valide les paramètres et résout les dépendances (injection du service)
4. Le service exécute la logique métier et met à jour les métriques custom
5. Le repository lit/écrit dans le store (mémoire pour l'instant)
6. La réponse est sérialisée (JSON ou HTML partial Jinja2) et renvoyée

## Démarrage de l'application

Le hook `lifespan` dans `main.py` s'exécute au démarrage :
1. Configuration des logs structurés (structlog → JSON stdout)
2. Instanciation du repository selon `config.yaml` (`storage.backend`)
3. Injection dans le service
4. `sync_active_gauge()` : la jauge Prometheus `todos_active` est resynchronisée avec l'état réel
   du store — essentiel lors de la migration vers un backend persistant

## Extension future

Voir [repository-pattern.md](repository-pattern.md) pour ajouter SQLite ou PostgreSQL.
Voir [monitoring.md](monitoring.md) pour comprendre chaque métrique et les logs.
