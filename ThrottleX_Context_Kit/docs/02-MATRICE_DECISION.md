# Matrice de Décision

## Algorithme Rate Limiting

| Critère | Sliding Window | Token Bucket | Fixed Window |
|---------|----------------|--------------|--------------|
| Précision | ★★★ | ★★☆ | ★☆☆ |
| Complexité | Moyenne | Faible | Faible |
| Bursts | Non | Oui | Non |

**Choix** : Sliding Window (principal) + Token Bucket (option)

## Stack Technique

| Composant | Choix | Justification |
|-----------|-------|---------------|
| API | FastAPI | Async, typage, OpenAPI auto |
| Storage | Redis | Atomicité Lua, TTL natif |
| Tests | pytest + hypothesis | Property-based testing |
