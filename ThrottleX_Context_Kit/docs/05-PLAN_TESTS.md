# Plan de Tests

## Tests Unitaires
```bash
pytest src/tests/unit/ -v --cov=src/throttlex --cov-report=term
```

## Tests Property (Hypothesis)
```bash
pytest src/tests/test_properties.py -v
```

Propriétés testées :
- Limite jamais dépassée
- Isolation entre tenants
- Fenêtre glissante correcte

## Tests de Charge (k6)
```bash
k6 run ThrottleX_Context_Kit/tests/k6/throttlex_load_test.js
```

Scénarios : 100 VUs pendant 30s

## Commande Complète
```bash
pytest --cov=src/throttlex --cov-report=html --cov-fail-under=80
```
