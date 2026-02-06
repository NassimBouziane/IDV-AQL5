"""Prometheus metrics for ThrottleX."""

from prometheus_client import Counter, Histogram, Info


class ThrottleXMetrics:
    """Metrics collection for ThrottleX."""

    def __init__(self) -> None:
        # Application info
        self.info = Info("throttlex", "ThrottleX Rate Limiter Service")
        self.info.info({"version": "0.1.0", "algorithm": "sliding_window"})

        # Request counters
        self.evaluate_total = Counter(
            "throttlex_evaluate_total",
            "Total number of rate limit evaluations",
            ["tenant_id", "route", "result"],
        )

        self.policies_total = Counter(
            "throttlex_policies_total",
            "Total number of policies created",
            ["tenant_id", "algorithm"],
        )

        self.http_requests_total = Counter(
            "throttlex_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        # Latency histograms
        self.evaluate_duration = Histogram(
            "throttlex_evaluate_duration_seconds",
            "Duration of rate limit evaluations",
            ["tenant_id"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        self.http_request_duration = Histogram(
            "throttlex_http_request_duration_seconds",
            "Duration of HTTP requests",
            ["method", "endpoint"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        # Redis metrics
        self.redis_operations_total = Counter(
            "throttlex_redis_operations_total",
            "Total Redis operations",
            ["operation", "status"],
        )

        self.redis_latency = Histogram(
            "throttlex_redis_latency_seconds",
            "Redis operation latency",
            ["operation"],
            buckets=[0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
        )


# Singleton instance
metrics = ThrottleXMetrics()
