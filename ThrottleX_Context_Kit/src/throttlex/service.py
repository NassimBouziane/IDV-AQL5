"""Rate limiting service."""

from typing import Optional

import structlog

from throttlex.config import get_settings
from throttlex.metrics import metrics
from throttlex.models import Algorithm, EvaluateRequest, EvaluateResponse, Policy
from throttlex.repository import RedisRepository, get_repository

logger = structlog.get_logger()


class RateLimiterService:
    """Service for rate limiting operations."""

    def __init__(self, repository: Optional[RedisRepository] = None) -> None:
        self._repository = repository or get_repository()
        self._settings = get_settings()

    async def create_policy(self, policy: Policy) -> Policy:
        """Create or update a policy."""
        saved = await self._repository.save_policy(policy)
        metrics.policies_total.labels(tenant_id=policy.tenant_id, algorithm=policy.algorithm.value).inc()
        logger.info(
            "policy_created",
            tenant_id=policy.tenant_id,
            route=policy.route,
            algorithm=policy.algorithm.value,
            limit=policy.limit,
        )
        return saved

    async def get_policies(self, tenant_id: str) -> list[Policy]:
        """Get all policies for a tenant."""
        return await self._repository.get_policies(tenant_id)

    async def delete_policy(self, tenant_id: str, route: Optional[str] = None) -> bool:
        """Delete a policy."""
        return await self._repository.delete_policy(tenant_id, route)

    async def evaluate(self, request: EvaluateRequest) -> tuple[EvaluateResponse, dict[str, int]]:
        """
        Evaluate if a request should be allowed.
        
        Returns: (response, headers_dict)
        """
        # Find matching policy
        policy = await self._repository.get_matching_policy(request.tenant_id, request.route)

        if policy is None:
            # No policy found - use defaults (allow with default limits)
            logger.warning(
                "no_policy_found",
                tenant_id=request.tenant_id,
                route=request.route,
            )
            # Create a default response (allow by default if no policy)
            policy = Policy(
                tenantId=request.tenant_id,
                route=request.route,
                scope="TENANT_ROUTE",
                algorithm=self._settings.default_algorithm,
                limit=self._settings.default_limit,
                windowSeconds=self._settings.default_window_seconds,
                burst=0,
            )

        # Evaluate based on algorithm
        if policy.algorithm == Algorithm.SLIDING_WINDOW:
            allow, remaining, reset_at = await self._repository.evaluate_sliding_window(
                request.tenant_id,
                request.route,
                policy.limit,
                policy.window_seconds,
                policy.burst,
            )
        else:
            # TOKEN_BUCKET: capacity = limit + burst, refill_rate = limit / window
            capacity = policy.limit + policy.burst
            refill_rate = policy.limit / policy.window_seconds
            allow, remaining, reset_at = await self._repository.evaluate_token_bucket(
                request.tenant_id,
                request.route,
                capacity,
                refill_rate,
            )

        # Record metrics
        result = "allowed" if allow else "blocked"
        metrics.evaluate_total.labels(
            tenant_id=request.tenant_id,
            route=request.route,
            result=result,
        ).inc()

        logger.info(
            "request_evaluated",
            tenant_id=request.tenant_id,
            route=request.route,
            allow=allow,
            remaining=remaining,
        )

        # Build response
        response = EvaluateResponse(
            allow=allow,
            remaining=remaining,
            resetAt=reset_at,
        )

        headers = {
            "X-RateLimit-Limit": policy.limit + policy.burst,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_at,
        }

        return response, headers


# Singleton instance
_service: Optional[RateLimiterService] = None


def get_service() -> RateLimiterService:
    """Get the service singleton."""
    global _service
    if _service is None:
        _service = RateLimiterService()
    return _service
