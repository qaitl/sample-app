# Monitoring système — Mac + containers Docker

Deux dashboards Grafana offrent une visibilité complète sur les ressources :

| Dashboard | Source | Contenu |
|-----------|--------|---------|
| **Node Exporter Full** | Grafana Labs #1860 | CPU, mémoire, disque, réseau, charge du Mac |
| **Cadvisor exporter** | Grafana Labs #14282 | CPU, mémoire, réseau par container Docker |

## Architecture

```
macOS (host)
  node_exporter :9100  ─────────────────────▶  prometheus  ──▶  grafana
                                                   ▲
Docker (todo-app-network)                          │
  cadvisor :8080  ────────────────────────────────┘
```

## Prérequis — installer node_exporter sur macOS

```bash
brew install node_exporter
brew services start node_exporter

# Vérifier que les métriques sont disponibles
curl -s http://localhost:9100/metrics | head -5
```

node_exporter démarre automatiquement au boot avec `brew services`.

## Démarrer la stack

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

Le service `cadvisor` démarre automatiquement avec la stack.

## Accéder aux dashboards

Ouvrir Grafana : **http://localhost:3000** (admin / admin)

- **Dashboards → Node Exporter Full** — métriques système du Mac
- **Dashboards → Cadvisor exporter** — métriques par container Docker

## Référence des ports

| Port | Service | Usage |
|------|---------|-------|
| 9100 | node_exporter (host) | Métriques système macOS |
| 8080 | cadvisor (Docker) | Métriques containers |
| 9091 | Prometheus | Interface de requêtes |
| 3000 | Grafana | Dashboards |

## Dépannage

**node-exporter DOWN dans Prometheus**
- Vérifier que le service tourne : `brew services list | grep node_exporter`
- Redémarrer : `brew services restart node_exporter`
- Tester : `curl http://localhost:9100/metrics`

**cadvisor DOWN dans Prometheus**
- Vérifier le container : `docker logs cadvisor`
- Relancer : `docker compose -f docker-compose.monitoring.yml restart cadvisor`

**Aucune donnée dans Node Exporter Full**
- S'assurer que Prometheus a bien rechargé sa config :
  ```bash
  docker compose -f docker-compose.monitoring.yml restart prometheus
  ```

**Métriques mémoire limitées sur macOS**
- node_exporter sur macOS expose moins de métriques mémoire que sur Linux.
  Certains panneaux du dashboard "Node Exporter Full" peuvent afficher N/A.
  Les panneaux CPU, disque et réseau fonctionnent correctement.
