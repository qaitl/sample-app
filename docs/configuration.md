# Configuration

## Fichier `config.yaml`

```yaml
app:
  host: "0.0.0.0"    # Interface d'écoute
  port: 8000          # Port uvicorn
  debug: false        # Mode debug FastAPI (affiche les erreurs dans les réponses)
  log_level: "INFO"   # Niveau de log : DEBUG | INFO | WARNING | ERROR

storage:
  backend: "memory"         # Backend de stockage : "memory" | "sqlite" | "postgresql"
  sqlite_path: "./todos.db" # Chemin du fichier SQLite (backend=sqlite uniquement)
  database_url: ""          # DSN PostgreSQL (backend=postgresql uniquement)
                            # ex: postgresql+asyncpg://user:pass@host:5432/db
```

## Surcharge par variables d'environnement

Le préfixe est `APP_` et le séparateur de niveaux est `__`.

| Variable d'environnement | Clé YAML | Exemple |
|---|---|---|
| `APP_APP__HOST` | `app.host` | `0.0.0.0` |
| `APP_APP__PORT` | `app.port` | `9000` |
| `APP_APP__DEBUG` | `app.debug` | `true` |
| `APP_APP__LOG_LEVEL` | `app.log_level` | `DEBUG` |
| `APP_STORAGE__BACKEND` | `storage.backend` | `sqlite` |
| `APP_STORAGE__SQLITE_PATH` | `storage.sqlite_path` | `/data/todos.db` |
| `APP_STORAGE__DATABASE_URL` | `storage.database_url` | `postgresql+asyncpg://...` |

**Priorité** (de la plus haute à la plus basse) :
1. Variables d'environnement
2. Fichier `config.yaml`
3. Valeurs par défaut du code

## Exemples Docker Compose

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - APP_APP__LOG_LEVEL=DEBUG     # surcharge du niveau de log
      - APP_APP__PORT=9000           # port différent
```

## Implémentation technique

La classe `YamlConfigSource` dans `src/config.py` implémente `PydanticBaseSettingsSource` pour
injecter les valeurs YAML dans la chaîne de résolution de `pydantic-settings`. Le singleton
`get_settings()` est mis en cache via `@lru_cache` pour éviter de relire le fichier à chaque appel.
