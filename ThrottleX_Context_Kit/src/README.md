# ThrottleX - Guide de Démarrage Rapide

## 1. Prérequis
- Python 3.11+
- Docker (pour Redis)

## 2. Installation

```powershell
# Depuis ce dossier (src/)
cd ThrottleX_Context_Kit\src

# Activer le venv (depuis src/)
..\..\.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -e ".[dev]"
```

## 3. Lancer Redis

```powershell
docker-compose up -d redis
```

## 4. Lancer l'API

```powershell
uvicorn throttlex.app:app --reload
```

API disponible sur http://localhost:8000

## 5. Lancer les Tests

```powershell
pytest --cov=throttlex --cov-report=term --cov-fail-under=80
```

## 6. Benchmarks (k6)

```powershell
k6 run ..\tests\k6\throttlex_load_test.js
```

## Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| POST | /policies | Créer politique |
| GET | /policies/{tenant} | Lister politiques |
| POST | /evaluate | Évaluer requête |
| GET | /health | Health check |
| GET | /metrics | Prometheus |

## API

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/policies` | Créer/mettre à jour une politique |
| GET | `/policies/{tenantId}` | Lister les politiques d'un tenant |
| DELETE | `/policies/{tenantId}` | Supprimer une politique |
| POST | `/evaluate` | Évaluer si une requête est autorisée |
| GET | `/health` | Health check |
| GET | `/metrics` | Métriques Prometheus |

### Exemples

```bash
# Créer une politique
curl -X POST http://localhost:8080/policies \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-free-01",
    "route": "/inference/text",
    "scope": "TENANT_ROUTE",
    "algorithm": "SLIDING_WINDOW",
    "limit": 60,
    "windowSeconds": 60,
    "burst": 20
  }'

# Évaluer une requête
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-free-01",
    "route": "/inference/text"
  }'
```

## Tests

```bash
# Tests unitaires
pytest tests/unit

# Tests d'intégration (nécessite Redis)
pytest tests/integration

# Couverture
pytest --cov=throttlex --cov-report=html
```

## Structure

```
src/
├── throttlex/
│   ├── __init__.py      # Version
│   ├── __main__.py      # Entry point
│   ├── app.py           # FastAPI application
│   ├── config.py        # Configuration settings
│   ├── models.py        # Pydantic models
│   ├── repository.py    # Redis repository
│   ├── service.py       # Business logic
│   ├── metrics.py       # Prometheus metrics
│   └── logging.py       # Structured logging
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml       # Project configuration
└── docker-compose.yml
```

