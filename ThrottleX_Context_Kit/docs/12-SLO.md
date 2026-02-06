# SLO (Service Level Objectives)

## Objectifs

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| Disponibilité | 99.9% | `/health` OK |
| Latence P50 | < 10ms | `/evaluate` |
| Latence P99 | < 50ms | `/evaluate` |
| Erreurs | < 0.1% | Status 5xx |

## SLIs (Indicateurs)

```promql
# Disponibilité
avg(up{job="throttlex"})

# Latence P99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Taux d'erreurs
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

## Alertes

- Dispo < 99% pendant 5min → Warning
- Latence P99 > 100ms → Warning
- Erreurs > 1% → Critical
