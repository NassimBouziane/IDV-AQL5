# Plan des Slides - Soutenance ThrottleX

## Slide 1 : Page de titre
- **ThrottleX** - Service de Rate Limiting Multi-tenant
- Projet IDV-AQL5 - Master 2
- Équipe : Nassim Bouziane, Thomas Boulard, Abdelkoudousse Boustani
- Date : Février 2026

---

## Slide 2 : Contexte et problématique
- APIs modernes exposées à des risques : surcharge, abus, DDoS
- Besoin de protéger les ressources backend
- Solution : Rate limiting intelligent et configurable
- **Objectif** : Concevoir un service robuste, testable et observable

---

## Slide 3 : Architecture globale
- Diagramme d'architecture (API Gateway → ThrottleX → Redis)
- Stack technique :
  - Python 3.11+ / FastAPI
  - Redis 7+ (stockage atomique Lua)
  - Docker / Docker Compose
- Patterns : Clean Architecture, Repository Pattern

---

## Slide 4 : Algorithmes de Rate Limiting
- **Sliding Window** : Compteur glissant avec burst
  - Simple, prévisible
  - Cas d'usage : APIs REST classiques
- **Token Bucket** : Jetons reconstitués progressivement
  - Lisse le trafic, autorise les bursts contrôlés
  - Cas d'usage : APIs avec pics de charge

---

## Slide 5 : API REST (OpenAPI)
- Endpoints principaux :
  - `POST /policies` - Créer une politique
  - `GET /policies/{tenant_id}` - Lister les politiques
  - `POST /evaluate` - Évaluer une requête
  - `GET /health` / `GET /ready` - Healthchecks
  - `GET /metrics` - Prometheus metrics
- Démo rapide de l'API (screenshot ou live)

---

## Slide 6 : Stratégie de tests
- **Tests unitaires** (72 tests)
  - Mocks Redis, tests isolés
  - Couverture : 89%
- **Tests d'intégration** (11 tests)
  - API HTTP mockée
- **Property-based testing** (Hypothesis)
  - Propriété : "Jamais plus de N requêtes autorisées dans une fenêtre"
- **Tests de charge** (k6)
  - 100 VUs, 10K requêtes

---

## Slide 7 : Pipeline CI/CD
- **GitHub Actions** + **GitLab CI** (double pipeline)
- Étapes :
  1. Lint (ruff check + format)
  2. Type checking (mypy)
  3. Tests unitaires + couverture (≥50%)
  4. Tests d'intégration
  5. Security scan (Bandit)
  6. Build Docker
- **Quality Gates** : Blocage automatique si seuil non atteint

---

## Slide 8 : Démonstration Quality Gate
- Scénario : Introduction d'une régression volontaire
  - Ex: Supprimer un import → erreur lint
  - Ex: Casser un test → couverture chute
- Résultat : **CI échoue** → merge bloqué
- Screenshot du pipeline rouge + explication

---

## Slide 9 : Benchmarks & Optimisation
- **Scripts** :
  - `benchmarks/benchmark_latency.py` (Python, mono/multi-client)
  - `benchmarks/benchmark_compare.py` (comparaison avant/après)
  - `tests/k6/throttlex_load_test.js` (test de charge)
- **Résultats mesurés** :
  - Mono-client (1000 req) : 248.64 req/s, P95 = 4.95ms, P99 = 6.28ms
  - Multi-client (20 VUs, 500 req) : 225.05 req/s, P95 = 319.88ms
- **Optimisations appliquées** :
  - Scripts Lua pré-chargés (SHA)
  - Pool Redis élargi (20 connexions)
  - Opérations atomiques
- Document : `BENCHMARK_RESULTS.md`

---

## Slide 10 : Observabilité
- **Métriques Prometheus** :
  - `throttlex_requests_total`
  - `throttlex_latency_seconds`
  - `throttlex_rate_limited_total`
- **Logs structurés** (structlog JSON)
- **Healthchecks** : `/health`, `/ready`
- Dashboard Grafana (optionnel) (on n'a pas fait nous)

---

## Slide 11 : Sécurité (SBOM + SAST)
- **SBOM** : Software Bill of Materials
  - Liste des dépendances avec versions
  - Généré via `pip-licenses` ou `cyclonedx-bom`
- **SAST** : Analyse statique (Bandit)
  - 0 vulnérabilités détectées
  - Règles : hardcoded passwords, injection, etc.

---

## Slide 12 : Documentation livrée
| Document | Description |
|----------|-------------|
| `RAPPORT_FINAL.md` | Rapport technique complet (~12 pages) |
| `SYNTHESE_ACTIVITE.md` | Résumé pour le jury (~5 pages) |
| `ADR/` | Decisions architecturales (3 ADRs) |
| `openapi/rate_limiter.yaml` | Spécification OpenAPI 3.1 |
| `RUNBOOK.md` | Guide opérationnel |
| `SLO.md` | Service Level Objectives |

---

## Slide 13 : Exécution locale
```bash
# Cloner et installer
git clone https://github.com/NassimBouziane/IDV-AQL5.git
cd IDV-AQL5/ThrottleX_Context_Kit/src
pip install -e ".[dev]"

# Lancer Redis + API
docker-compose up -d redis
uvicorn throttlex.app:app --reload

# Lancer les tests
pytest tests/unit -v --cov=throttlex
```

---

## Slide 14 : Bilan et perspectives
### Ce qui fonctionne ✅
- API fonctionnelle avec 2 algorithmes
- Pipeline CI/CD robuste
- Tests complets (unit, integ, property, load)
- Documentation exhaustive

### Améliorations possibles
- Clustering Redis (Sentinel/Cluster) (Note : Les latences multi-client sont élevées car tous les workers partagent le même pool Redis local. En production avec Redis Cluster, les performances seraient meilleures.)
- Dashboard Grafana pré-configuré
- Rate limiting distribué (multi-région)

---

## Slide 15 : Questions ?
- Merci de votre attention
- Liens :
  - GitHub : `github.com/NassimBouziane/IDV-AQL5`
  - Lien CI : (actions tab)
- Contact équipe

---

## Notes pour la démo live

### Scénario 1 : Démontrer l'API
1. Créer une policy : `curl -X POST /policies`
2. Faire plusieurs appels : `curl -X POST /evaluate`
3. Montrer le rate limiting en action (429)

### Scénario 2 : Quality Gate bloquée
1. Modifier un fichier pour casser le lint
2. Commit + push
3. Montrer la CI qui échoue
4. Revert et montrer la CI verte

### Scénario 3 : Benchmark
1. Lancer `k6 run throttlex_load_test.js`
2. Montrer les résultats en temps réel
