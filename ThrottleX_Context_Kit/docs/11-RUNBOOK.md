# Runbook

## Incidents Courants

### Redis Down

**Symptôme** : `/health` retourne "degraded"

**Actions** :
1. Vérifier container : `docker ps | grep redis`
2. Redémarrer : `docker-compose restart redis`
3. Vérifier logs : `docker logs redis`

### Rate Limit Bloqué

**Symptôme** : Toutes requêtes rejetées (429)

**Actions** :
1. Vérifier politique : `GET /policies/{tenant}`
2. Ajuster limite si nécessaire
3. Reset compteur Redis si urgence

### Latence Élevée

**Symptôme** : P99 > 100ms

**Actions** :
1. Vérifier métriques : `GET /metrics`
2. Vérifier charge Redis : `redis-cli INFO stats`
3. Scaler horizontalement si besoin
