# ThrottleX — Context Pack (IDV-AQL5)

Ce pack donne un **contexte concret** au sujet *ThrottleX : Rate Limiting & Quotas* et se compose de :
- un **scénario narratif** (API publique protégée) ;
- un **contrat OpenAPI** pour le service de **rate limit** ;
- un **contrat OpenAPI** minimal pour une API **démonstration** (inférence simulée) ;
- un **jeu de données** de **tenants / offres** ;
- un **harnais de bench** (k6) paramétrable ;
- une **checklist CI** pour industrialiser.

> Vous restez libres de la stack pour l'implémentation. Le pack fournit uniquement le **contrat** et un **cadre de mesure**.

---

## 1) Scénario : API publique « Inference Demo » protégée par ThrottleX

Votre entreprise propose une API d’**inférence** (texte → texte). Chaque requête **coûte** et la charge varie fortement.
Objectif : **protéger** l’API contre les abus, garantir une **expérience équitable** entre clients et **maîtriser les coûts**.

- **Tiers & quotas** (exemple) :
  - *Free* : 60 req/min, burst 20
  - *Pro* : 600 req/min, burst 100
  - *Enterprise* : 3000 req/min, burst 600
- **Fairness** : éviter le *bruit de voisinage* (un client ne doit pas affamer les autres).
- **Observabilité** : métriques `allow/blocked`, p95/p99, erreurs.
- **Headers** usuels : `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

Flux (simplifié) :
1. Client → `POST /evaluate` (ThrottleX) avec `{tenantId, route}`
2. Si `allow=true`, le client appelle l’API `POST /inference/text`
3. L’API relaie (ou enrichit) les **headers** de quota dans la réponse.

---

## 2) Artefacts fournis

- `openapi/rate_limiter.yaml` : contrat du service de limitation (policies, evaluate).
- `openapi/demo_api.yaml` : contrat minimal pour une API d’inférence **simulée**.
- `data/tenants.json` : échantillon de *tenants* et **offres** (Free/Pro/Enterprise).
- `tests/k6/throttlex_load_test.js` : script de charge paramétrable (mono/multi-clients).
- `ci/README_CI.md` : checklist de **quality gates**.

---

## Utilisation rapide

1. **Décidez** de votre architecture (A : *stateless + KV* / B : *in-memory + sticky*), documentez via matrice + ADR.
2. **Implémentez** le service ThrottleX conforme à `openapi/rate_limiter.yaml`.
3. **Optionnel** : implémentez l’API *Inference Demo* (ou moquez-la), conforme à `openapi/demo_api.yaml`.
4. **Mesurez** avec `tests/k6/throttlex_load_test.js` (voir variables d’environnement en tête de fichier).
5. **Industrialisez** (CI) selon `ci/README_CI.md`.

> Tous les éléments sont volontairement **minimalistes** pour rester centrés sur l’architecture, l’audit, les tests et les benchmarks.
