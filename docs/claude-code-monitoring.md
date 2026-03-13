# Claude Code Monitoring

Ce document explique comment visualiser la télémétrie Claude Code (coût, tokens,
sessions, performance des outils) dans le Grafana de la stack sample-app.

> Repo source de la stack dédiée : <https://github.com/qaitl/claude-code-monitoring>

## Architecture

Claude Code CLI émet de la télémétrie OpenTelemetry. Le pipeline est le suivant :

```
Claude Code CLI (host)
        │ OTLP gRPC :4317 / HTTP :4318
        ▼
  otel-collector           (Docker, todo-app-network)
        ├── métriques ──────▶ prometheus :8889 scrape ──▶ Grafana
        └── logs (OTLP) ────▶ loki /otlp              ──▶ Grafana
```

L'OTel Collector est intégré dans la stack existante (`docker-compose.monitoring.yml`).
Aucun service Prometheus ou Loki supplémentaire n'est nécessaire.

## Démarrer la stack

```bash
# Créer le réseau Docker si ce n'est pas encore fait
docker network create todo-app-network

# Démarrer (ou redémarrer) toute la stack de monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

## Configurer Claude Code

Ajouter les variables suivantes à votre shell (`~/.zshrc` ou `~/.bashrc`) :

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=5000   # 5s — évite de perdre les compteurs one-shot
export OTEL_LOGS_EXPORT_INTERVAL=5000
```

Recharger le shell puis démarrer une session Claude Code normalement.

## Accéder au dashboard

Ouvrir Grafana : **<http://localhost:3000>** (admin / admin)

Naviguer vers **Dashboards → Claude Code**.

Le dashboard contient 33 panneaux répartis en 8 sections :

| Section | Contenu |
|---------|---------|
| Overview | Coût cycle facturation, tokens totaux, sessions |
| Productivity | Commits, PRs, lignes ajoutées/supprimées, code edits |
| Sessions & Activity | Durée moyenne, temps actif, coût/heure |
| Trends | Débit coût et tokens par modèle (séries temporelles) |
| Cost Analysis | Coût et tokens par modèle et par utilisateur |
| Performance | Latence API, taux d'erreur (via logs Loki) |
| Token & Efficiency | Cache hit rate, répartition input/output/cache |
| Insights | Usage des outils, décisions d'édition, log des événements |

## Référence des ports

| Port | Protocole | Usage |
|------|-----------|-------|
| 4317 | gRPC | Récepteur OTLP — point de connexion du CLI |
| 4318 | HTTP | Récepteur OTLP — protocole alternatif |
| 9091 | HTTP | Interface Prometheus |
| 3000 | HTTP | Interface Grafana |
| 3100 | HTTP | API Loki |

## Dépannage

**Aucune donnée dans le dashboard**
- Vérifier que le collecteur tourne : `docker logs otel-collector`
- Vérifier que `CLAUDE_CODE_ENABLE_TELEMETRY=1` est bien exporté dans le shell courant
- Vérifier que la cible `otel-collector` est UP dans Prometheus : <http://localhost:9091/targets>

**Loki rejette les logs (HTTP 400)**
- Vérifier que `allow_structured_metadata: true` est présent dans `monitoring/loki/loki-config.yaml`
- Redémarrer Loki : `docker compose -f docker-compose.monitoring.yml restart loki`

**Conflit sur les ports 4317/4318**
- La stack standalone `claude-code-monitoring` utilise les mêmes ports.
  Les deux stacks ne peuvent pas tourner simultanément.
  Arrêter l'autre stack avant de démarrer celle-ci.
