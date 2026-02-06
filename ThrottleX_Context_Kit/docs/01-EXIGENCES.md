# Exigences ThrottleX

## Fonctionnelles
| ID | Exigence | Priorité |
|----|----------|----------|
| F1 | Limiter requêtes par tenant (sliding window) | Haute |
| F2 | Token Bucket alternatif | Moyenne |
| F3 | Configuration multi-tenant | Haute |
| F4 | Métriques Prometheus | Moyenne |

## Non-Fonctionnelles
| ID | Exigence | Cible |
|----|----------|-------|
| NF1 | Latence P99 | < 50ms |
| NF2 | Disponibilité | 99.9% |
| NF3 | Couverture tests | ≥ 80% |

## Contraintes
- Python 3.11+, FastAPI, Redis 7+
- Déploiement Docker/Kubernetes
