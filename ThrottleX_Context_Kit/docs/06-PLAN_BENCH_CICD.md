# Plan de Benchmarks et CI/CD

## Benchmarks

### Scénarios k6
| Scénario | VUs | Durée |
|----------|-----|-------|
| Smoke | 5 | 30s |
| Load | 50 | 60s |
| Stress | 100 | 60s |

### Métriques mesurées
- Latence p95, p99
- Throughput (req/s)
- Taux d'erreur

### Commandes
```bash
k6 run tests/k6/throttlex_load_test.js
```

## CI/CD

### Pipeline GitLab
```
lint → test → security → build
```

### Jobs
| Job | Description |
|-----|-------------|
| lint | ruff check |
| test:unit | pytest + couverture |
| sast | bandit |
| sbom | cyclonedx-bom |

### Quality Gates
- Tests : 100% pass
- Couverture : ≥80%
- SAST : 0 vulnérabilité haute
