# Benchmarks

## Outil : k6

```bash
k6 run tests/k6/throttlex_load_test.js
```

## Scénarios

| Scénario | VUs | Durée | Objectif |
|----------|-----|-------|----------|
| Baseline | 10 | 30s | Latence P50 < 10ms |
| Load | 100 | 1min | P99 < 50ms |
| Stress | 500 | 2min | Pas d'erreurs |

## Résultats Attendus

- Throughput : > 5000 req/s
- Latence P99 : < 50ms
- Erreurs : < 0.1%
