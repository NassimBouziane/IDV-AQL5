# ADR-004 : Stratégie de tests avec Hypothesis

**Date** : 2026-02-06  
**Statut** : Accepté

## Contexte

Les tests unitaires classiques ne suffisent pas pour garantir les invariants du rate limiting. Il faut tester les propriétés du système.

## Options

### A. Tests unitaires uniquement
- Simple
- Ne couvre pas tous les edge cases

### B. Tests de propriétés (Hypothesis)
- Génère des cas de test automatiquement
- Trouve les edge cases
- Plus complexe à écrire

### C. Tests de mutation
- Vérifie la qualité des tests
- Complexe à mettre en place

## Décision

Combiner **tests unitaires** et **tests de propriétés avec Hypothesis**.

## Justification

1. **Invariant critique** : "Jamais > N requêtes dans la fenêtre"
2. **Edge cases** : Hypothesis génère des valeurs limites automatiquement
3. **Confiance** : Prouve mathématiquement les propriétés

## Propriétés testées

```python
# Jamais plus de limit requêtes autorisées
@given(limit=st.integers(min_value=1, max_value=100))
def test_never_exceeds_limit(limit):
    # Faire limit+10 requêtes
    # Vérifier que <= limit sont allowed
```

## Conséquences

- ✅ Haute confiance dans la logique métier
- ✅ Découverte automatique de bugs
- ⚠️ Tests plus lents (génération aléatoire)
- ⚠️ Courbe d'apprentissage Hypothesis
