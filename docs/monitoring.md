# Monitoring

## Vue d'ensemble du pipeline

```
Application (stdout JSON)
        │
        ▼
   Promtail (sidecar Docker)
        │  push
        ▼
      Loki  ←──── Grafana
                      ▲
      Prometheus ──────┘
        ▲
        │ scrape /metrics
   Application (FastAPI)
```

## Métriques Prometheus

### Métriques HTTP automatiques

Fournies par `prometheus-fastapi-instrumentator` sans code supplémentaire.

> **Alternatives envisagées**
>
> - **`prometheus_client` manuel** — bibliothèque officielle bas niveau. On définit soi-même chaque
>   `Counter`, `Histogram`, `Gauge` et on expose `/metrics` via `make_asgi_app()`. Plus verbeux,
>   mais contrôle total sur le nommage et les labels. Pédagogiquement utile pour comprendre
>   l'instrumentation depuis zéro.
> - **`starlette-exporter`** — alternative légère à `prometheus-fastapi-instrumentator`, spécifique
>   à Starlette/FastAPI, avec moins d'options de configuration.

| Métrique | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | Nombre total de requêtes, labels : `handler`, `method`, `status` |
| `http_request_duration_seconds` | Histogram | Durée des requêtes (buckets), permet P50/P95/P99 |
| `http_requests_in_progress` | Gauge | Requêtes en cours à l'instant t |

### Métriques custom (domaine métier)

Définies dans `src/services/todo_service.py` — seul endroit qui les incrémente.

| Métrique | Type | Description |
|---|---|---|
| `todos_created_total` | Counter | Incrémenté à chaque `create_todo()` |
| `todos_completed_total` | Counter | Incrémenté à chaque transition `completed=False → True` |
| `todos_active` | Gauge | Nombre de todos non complétés. Décrémenté à la complétion ou suppression, incrémenté à la création |

#### Pourquoi une Gauge pour `todos_active` ?

Un Counter ne peut qu'augmenter. `todos_active` doit descendre quand une tâche est complétée ou
supprimée — c'est donc une Gauge.

**Problème du redémarrage** : après un redémarrage avec stockage en mémoire, la Gauge repart à 0
(correct car les données sont perdues). Avec un backend persistant (SQLite/PostgreSQL), la méthode
`sync_active_gauge()` est appelée au démarrage du lifespan pour re-lire le compte réel depuis la
base.

## Logs structurés → Loki

### Format de log

L'application utilise `structlog` configuré pour émettre du JSON sur stdout :

```json
{"timestamp": "2025-03-12T10:00:00Z", "level": "info", "logger": "src.api.v1.todos", "event": "todo_created", "todo_id": "abc-123", "title": "Acheter du pain", "request_id": "f47ac10b-58cc-..."}
```

Chaque requête HTTP reçoit un `request_id` unique (header `X-Request-ID` ou UUID généré) injecté
dans le contexte structlog via `structlog.contextvars`. Toutes les lignes de log d'une même
requête partagent ce `request_id`, ce qui permet de corréler les logs dans Grafana Loki.

### Pipeline Promtail — deux modes

Promtail expose deux jobs selon l'environnement d'exécution de l'application :

#### Mode dev local (app hors Docker)

L'application tourne avec `uvicorn --reload` sur l'hôte. Promtail ne peut pas découvrir son
processus via le socket Docker. La solution : rediriger stdout vers un fichier partagé.

```bash
uv run uvicorn src.main:app --reload 2>&1 | tee logs/app.log
```

Le répertoire `logs/` est monté en lecture seule dans le container Promtail (`./logs:/logs:ro`).
Promtail lit `/logs/app.log` via un job `static_configs` et pousse les lignes JSON vers Loki.

#### Mode production Docker (app dans un container)

Promtail découvre automatiquement le container `sample-app` via le socket Docker
(`/var/run/docker.sock`) et collecte les logs de son stdout.

#### Pipeline commun aux deux modes

1. Parse les champs JSON (`level`, `event`, `request_id`) avec `pipeline_stages.json`
2. Promeut `level` et `request_id` en labels Loki
3. Pousse vers Loki via HTTP — label `container="sample-app"` dans les deux cas

### Requêtes Loki utiles

```logql
# Tous les logs de l'app
{container="sample-app"}

# Erreurs uniquement
{container="sample-app", level="error"}

# Logs d'une requête spécifique
{container="sample-app"} | json | request_id="<uuid>"

# Volume par niveau sur 1m
sum(count_over_time({container="sample-app"}[1m])) by (level)
```

## Dashboard Grafana

Le dashboard `monitoring/grafana/dashboards/todo-app.json` est provisionné automatiquement au
démarrage de Grafana.

### Ligne 1 — HTTP Traffic

| Panneau | Query | Utilité |
|---|---|---|
| Request Rate | `rate(http_requests_total{job="todo-app"}[$__rate_interval])` | Volume de trafic par handler |
| Error Rate (5xx) | `rate(http_requests_total{..., status=~"5.."}[$__rate_interval])` | Alerting immédiat |
| P95 Latency | `histogram_quantile(0.95, ...)` | Latence perçue par 95% des utilisateurs |
| Active Requests | `http_requests_in_progress` | Détection de blocages |

### Ligne 2 — Business Metrics

| Panneau | Query | Utilité |
|---|---|---|
| Todos Created (rate) | `rate(todos_created_total[$__rate_interval])` | Activité des utilisateurs |
| Todos Completed (rate) | `rate(todos_completed_total[$__rate_interval])` | Taux de complétion |
| Active Todos (gauge) | `todos_active` | État instantané, thresholds : vert<10 / jaune<20 / rouge≥20 |
| Total Created | `todos_created_total` | Compteur absolu depuis le démarrage |

> `$__rate_interval` est une variable built-in Grafana (≥ 4× le scrape interval) recommandée pour
> les fonctions `rate()` et `irate()` — contrairement à une variable personnalisée, elle est
> toujours résolue avant l'envoi à Prometheus.

### Ligne 3 — Logs

| Panneau | Query | Utilité |
|---|---|---|
| Application Logs | `{container="sample-app"}` | Flux complet |
| Error Logs | `{container="sample-app", level="error"}` | Anomalies |
| Log Volume | `sum(count_over_time({container="sample-app"}[$__interval])) by (level)` | Tendance du bruit |

### Accès Grafana

URL : `http://localhost:3000` — identifiants par défaut : `admin / admin`

---

## Cible Prometheus selon le mode de déploiement

La cible de scrape dans `monitoring/prometheus/prometheus.yml` doit être adaptée selon où tourne
l'application :

| Mode | Valeur `targets` | Cas d'usage |
|---|---|---|
| **Full Docker** (`docker compose up`) | `sample-app:8000` | Tous les services dans le même réseau Docker |
| **Dev local** (app hors Docker, macOS) | `host.docker.internal:8000` | App lancée avec `uvicorn --reload`, stack monitoring en Docker |

`host.docker.internal` est un hostname spécial fourni par Docker Desktop sur macOS/Windows qui
résout vers l'adresse IP de la machine hôte. Il n'existe pas sur Linux (utiliser `172.17.0.1` ou
`--add-host=host.docker.internal:host-gateway` dans le compose).

Le réseau `todo-app-network` doit exister avant de démarrer la stack monitoring (il est créé
automatiquement par `docker compose up`, ou manuellement avec `docker network create todo-app-network`).

---

## Logs Loki en mode dev local (macOS)

**Statut : fonctionnel — push HTTP direct vers Loki**

### Contexte

En mode dev local sur macOS, Promtail ne peut pas détecter les nouvelles lignes écrites dans
`logs/app.log` via un volume bind-monté (`./logs:/logs:ro`). Docker Desktop virtualise Linux dans
une VM : les événements `inotify` générés par les écritures sur l'hôte macOS ne se propagent pas
dans le container Linux. Promtail ne voit jamais les nouvelles lignes.

Ce comportement est une limitation connue de Docker Desktop (macOS et Windows). Il n'affecte pas
les déploiements full-Docker ni les environnements Linux natifs.

### Solution retenue : push HTTP direct vers Loki

Plutôt que de passer par Promtail pour le fichier de log, l'application pousse ses logs
directement vers Loki via HTTP avec `python-logging-loki`.

**Configuration** (`config.yaml`) :

```yaml
app:
  loki_url: "http://localhost:3100/loki/api/v1/push"  # vide "" pour désactiver
```

**Comportement** :
- Si `loki_url` est non vide au démarrage, un `LokiHandler` est ajouté au logger Python racine.
- Les logs structlog (JSON stdout) sont envoyés en parallèle vers Loki via HTTP.
- En production Docker, `loki_url` reste vide — Promtail collecte les logs du container
  via le socket Docker (pas de problème d'inotify en full-Docker).

**Labels Loki en mode dev** :

```logql
{container="sample-app", env="dev"}
```

**Implémentation** (`src/main.py`) :

```python
def configure_logging(log_level: str = "INFO", loki_url: str = "") -> None:
    ...
    if loki_url:
        import logging_loki
        logging_loki.emitter.LokiEmitter.level_tag = "level"
        loki_handler = logging_loki.LokiHandler(
            url=loki_url,
            tags={"container": "sample-app", "env": "dev"},
            version="1",
        )
        loki_handler.setLevel(level)
        logging.getLogger().addHandler(loki_handler)
```
