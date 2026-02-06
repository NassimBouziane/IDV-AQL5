"""Domain models for ThrottleX."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Scope(StrEnum):
    """Policy scope."""

    TENANT = "TENANT"
    TENANT_ROUTE = "TENANT_ROUTE"


class Algorithm(StrEnum):
    """Rate limiting algorithm."""

    SLIDING_WINDOW = "SLIDING_WINDOW"
    TOKEN_BUCKET = "TOKEN_BUCKET"  # noqa: S105  # nosec B105


class Policy(BaseModel):
    """Rate limiting policy for a tenant."""

    tenant_id: str = Field(..., alias="tenantId", min_length=1, max_length=255)
    route: str | None = Field(None, max_length=500)
    scope: Scope
    algorithm: Algorithm
    limit: int = Field(..., ge=1)
    window_seconds: int = Field(..., alias="windowSeconds", ge=1)
    burst: int = Field(0, ge=0)
    ttl_seconds: int | None = Field(None, alias="ttlSeconds", ge=1)

    model_config = ConfigDict(populate_by_name=True)

    def get_key(self) -> str:
        """Generate unique key for this policy."""
        if self.route:
            return f"policy:{self.tenant_id}:{self.route}"
        return f"policy:{self.tenant_id}:*"


class EvaluateRequest(BaseModel):
    """Request to evaluate rate limit."""

    tenant_id: str = Field(..., alias="tenantId", min_length=1)
    route: str = Field(..., min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class EvaluateResponse(BaseModel):
    """Response from rate limit evaluation."""

    allow: bool
    remaining: int | None = None
    reset_at: int | None = Field(None, alias="resetAt")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
