"""Domain models for ThrottleX."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Scope(str, Enum):
    """Policy scope."""

    TENANT = "TENANT"
    TENANT_ROUTE = "TENANT_ROUTE"


class Algorithm(str, Enum):
    """Rate limiting algorithm."""

    SLIDING_WINDOW = "SLIDING_WINDOW"
    TOKEN_BUCKET = "TOKEN_BUCKET"


class Policy(BaseModel):
    """Rate limiting policy for a tenant."""

    tenant_id: str = Field(..., alias="tenantId", min_length=1, max_length=255)
    route: Optional[str] = Field(None, max_length=500)
    scope: Scope
    algorithm: Algorithm
    limit: int = Field(..., ge=1)
    window_seconds: int = Field(..., alias="windowSeconds", ge=1)
    burst: int = Field(0, ge=0)
    ttl_seconds: Optional[int] = Field(None, alias="ttlSeconds", ge=1)

    class Config:
        populate_by_name = True

    def get_key(self) -> str:
        """Generate unique key for this policy."""
        if self.route:
            return f"policy:{self.tenant_id}:{self.route}"
        return f"policy:{self.tenant_id}:*"


class EvaluateRequest(BaseModel):
    """Request to evaluate rate limit."""

    tenant_id: str = Field(..., alias="tenantId", min_length=1)
    route: str = Field(..., min_length=1)

    class Config:
        populate_by_name = True


class EvaluateResponse(BaseModel):
    """Response from rate limit evaluation."""

    allow: bool
    remaining: Optional[int] = None
    reset_at: Optional[int] = Field(None, alias="resetAt")

    class Config:
        populate_by_name = True
        by_alias = True
