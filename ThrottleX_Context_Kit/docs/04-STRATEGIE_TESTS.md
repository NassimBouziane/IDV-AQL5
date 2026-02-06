# Stratégie de Tests

## Pyramide
```
     /\
    /  \  E2E (k6)
   /----\
  / Intég \ (Redis)
 /----------\
/  Unitaires  \ (mocks)
```

## Couverture par Module

| Module | Cible | Tests Clés |
|--------|-------|------------|
| service.py | 100% | evaluate_request, token_bucket |
| repository.py | 80% | incr_and_check, Lua scripts |
| app.py | 70% | endpoints, error handling |

## Scénarios Property Testing
- `test_limit_never_exceeded`: jamais > max requests
- `test_tenant_isolation`: tenants indépendants
- `test_window_reset`: reset après expiration
