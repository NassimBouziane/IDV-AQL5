# ADR-002 : Choix de l'algorithme par défaut

**Date** : 2026-02-06  
**Statut** : Accepté

## Contexte

ThrottleX doit supporter plusieurs algorithmes de rate limiting. Il faut choisir lequel utiliser par défaut.

## Options

### A. Sliding Window (Fenêtre glissante)
- Simple à implémenter
- Compteur atomique avec TTL
- Bonne précision

### B. Token Bucket
- Plus flexible (burst natif)
- Plus complexe (état à maintenir)
- Meilleure lissage du trafic

## Décision

**Sliding Window** comme algorithme par défaut.

## Justification

1. **Simplicité** : 1 compteur Redis vs structure complexe
2. **Atomicité** : Script Lua simple et efficace
3. **Suffisant** : Couvre 90% des cas d'usage
4. **Token Bucket disponible** : En option pour cas avancés

## Conséquences

- ✅ Implémentation rapide
- ✅ Moins de bugs potentiels
- ⚠️ Burst moins "smooth" qu'avec Token Bucket
- ⚠️ Fenêtres fixes (pas de vraie sliding window)
