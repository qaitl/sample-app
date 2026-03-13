# Développement local

## Prérequis

- [uv](https://docs.astral.sh/uv/) >= 0.9
- Docker + Docker Compose v2 (pour la stack monitoring)
- Python 3.13 (géré automatiquement par uv)

## Premier démarrage

```bash
# Cloner le dépôt et entrer dans le répertoire
cd sample-app

# Installer les dépendances (runtime + dev)
uv sync

# Démarrer en mode développement (rechargement automatique)
uv run uvicorn src.main:app --reload

# L'application est disponible sur :
# http://localhost:8000       → interface todo
# http://localhost:8000/docs  → documentation OpenAPI
# http://localhost:8000/metrics → métriques Prometheus
# http://localhost:8000/health  → health-check
```

## Commandes utiles

```bash
# Tests
uv run pytest tests/ -v

# Tests avec couverture
uv run pytest tests/ --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/ tests/

# Lint avec correction automatique
uv run ruff check --fix src/ tests/

# Vérification des types
uv run mypy src/
```

## Démarrage avec Docker

```bash
# Build et démarrage de l'application seule
docker compose up --build

# Démarrage de la stack monitoring (nécessite que l'app soit démarrée d'abord)
docker compose -f docker-compose.monitoring.yml up -d

# Accès Grafana : http://localhost:3000 (admin / admin)
# Accès Prometheus : http://localhost:9090
```

## Générer de la charge pour tester le monitoring

```bash
# Créer 20 todos
for i in $(seq 1 20); do
  curl -s -X POST http://localhost:8000/api/v1/todos \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"Task $i\"}"
done

# Lister les todos
curl -s http://localhost:8000/api/v1/todos | python3 -m json.tool

# Vérifier les métriques
curl -s http://localhost:8000/metrics | grep todos_
```

## Surcharge de configuration en développement

```bash
# Mode debug avec logs verbeux
APP_APP__DEBUG=true APP_APP__LOG_LEVEL=DEBUG uv run uvicorn src.main:app --reload
```

## Structure des répertoires

```
src/               Code source Python
templates/         Templates Jinja2 (HTML)
static/            Fichiers statiques (CSS, HTMX)
tests/             Tests pytest
monitoring/        Configurations Prometheus, Loki, Promtail, Grafana
docs/              Documentation (ce répertoire)
config.yaml        Configuration par défaut
```
