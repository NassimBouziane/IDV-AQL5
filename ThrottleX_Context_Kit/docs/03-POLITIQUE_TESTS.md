# Politique de Tests

## Objectifs
- Couverture minimale : **80%**
- Tous les tests passent avant merge
- Property-based testing pour invariants

## Types de Tests

| Type | Outil | Scope |
|------|-------|-------|
| Unitaires | pytest | Fonctions isolées |
| Property | hypothesis | Invariants (limites, isolation) |
| Intégration | pytest + testcontainers | Redis réel |
| Charge | k6 | Performance |

## Règles
1. Pas de code sans test associé
2. Mock Redis pour tests unitaires
3. Tests property pour comportements critiques
