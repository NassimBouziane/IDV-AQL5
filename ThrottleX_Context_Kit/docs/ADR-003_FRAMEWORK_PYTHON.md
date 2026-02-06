# ADR-003 : Choix du framework Python

**Date** : 2026-02-06  
**Statut** : Accepté

## Contexte

Choix du framework pour implémenter l'API REST de ThrottleX.

## Options

### A. FastAPI
- Async natif
- Validation Pydantic intégrée
- OpenAPI auto-généré
- Performant

### B. Flask
- Simple et mature
- Grande communauté
- Sync par défaut

### C. Django REST Framework
- Très complet
- Trop lourd pour notre cas

## Décision

**FastAPI** pour l'API ThrottleX.

## Justification

1. **Async** : Essentiel pour les appels Redis non-bloquants
2. **Performance** : Parmi les plus rapides en Python
3. **Validation** : Pydantic natif = moins de code
4. **OpenAPI** : Documentation auto-générée
5. **Moderne** : Type hints, async/await

## Conséquences

- ✅ Latence réduite grâce à async
- ✅ Validation des entrées automatique
- ✅ Documentation API sans effort
- ⚠️ Courbe d'apprentissage async
- ⚠️ Moins de ressources/tutoriels que Flask
