# ThrottleX — Rate Limiting & Quotas Multi-Tenant

Service de rate limiting pour API, développé dans le cadre du module IDV-AQL5.

## 🚀 Démarrage rapide

### Prérequis
- Python 3.11+
- Docker (pour Redis)

### Installation

```bash
# 1. Cloner et entrer dans le dossier
cd ThrottleX_Context_Kit

# 2. Lancer Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 3. Créer et activer un venv (optionnel mais recommandé)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# 4. Installer les dépendances
pip install fastapi "uvicorn[standard]" redis pydantic pydantic-settings prometheus-client structlog pytest pytest-asyncio pytest-cov httpx fakeredis hypothesis ruff bandit

# 5. Lancer le serveur
cd src
$env:PYTHONPATH="$PWD"  # PowerShell Windows
# export PYTHONPATH=$PWD  # Linux/Mac
python -m uvicorn throttlex.app:app --reload
```

### Tester les endpoints

```bash
# Health check
curl http://localhost:8080/health

# Créer une policy
curl -X POST http://localhost:8080/policies -H "Content-Type: application/json" -d '{"tenantId":"t1","scope":"TENANT","algorithm":"SLIDING_WINDOW","limit":100,"windowSeconds":60}'

# Évaluer une requête
curl -X POST http://localhost:8080/evaluate -H "Content-Type: application/json" -d '{"tenantId":"t1","route":"/"}'
```

## 📁 Structure

```
ThrottleX_Context_Kit/
├── src/throttlex/          # Code applicatif
├── docs/                   # Documentation
├── openapi/                # Contrats API
├── tests/k6/               # Scripts de charge
└── .github/workflows/      # CI/CD
```

## 📝 Documentation

- [Guide Projet](GUIDE_PROJET.md) — Checklist des étapes
- [Exigences](docs/01-EXIGENCES.md)
- [Architecture](docs/07-DIAGRAMMES_ARCHITECTURE.md)
- [OpenAPI](openapi/rate_limiter.yaml)

## 🧪 Tests

```bash
cd src
pytest --cov=throttlex
```

## 👥 Équipe

Projet Master 2 — Module IDV-AQL5 Qualité du Code
