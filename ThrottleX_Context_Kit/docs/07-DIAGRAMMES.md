# Diagrammes d'Architecture

## Contexte
```
┌─────────┐       ┌───────────┐       ┌─────────┐
│ Client  │──────▶│ ThrottleX │──────▶│  Redis  │
│  API    │◀──────│ (FastAPI) │◀──────│ (Store) │
└─────────┘       └───────────┘       └─────────┘
```

## Composants
```
ThrottleX
├── app.py         # Endpoints FastAPI
├── service.py     # Logique métier
├── repository.py  # Accès Redis
└── models.py      # Modèles Pydantic
```

## Séquence Evaluate
```
Client → ThrottleX → Redis (Lua script) → ThrottleX → Client
                    ↓
              allow/block
```

## Déploiement
```
┌──────────────────────────────┐
│         Kubernetes           │
│  ┌──────────┐  ┌──────────┐  │
│  │ ThrottleX│  │ ThrottleX│  │
│  │  Pod 1   │  │  Pod 2   │  │
│  └────┬─────┘  └────┬─────┘  │
│       └──────┬──────┘        │
│              ▼               │
│        ┌──────────┐          │
│        │  Redis   │          │
│        └──────────┘          │
└──────────────────────────────┘
```
