#!/usr/bin/env python3
"""
Benchmark script for ThrottleX latency measurements.

Measures p50, p95, p99 latency and throughput for:
- Mono-client (sequential requests)
- Multi-client (concurrent requests with asyncio)

Usage:
    python benchmark_latency.py --url http://localhost:8000 --requests 1000
    python benchmark_latency.py --url http://localhost:8000 --concurrent 50 --requests 5000
"""

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class BenchmarkResult:
    """Benchmark result metrics."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    allowed_requests: int
    blocked_requests: int
    total_duration_seconds: float
    latencies_ms: list[float]

    @property
    def throughput(self) -> float:
        """Requests per second."""
        return self.total_requests / self.total_duration_seconds

    @property
    def p50(self) -> float:
        """50th percentile latency in ms."""
        return self._percentile(50)

    @property
    def p95(self) -> float:
        """95th percentile latency in ms."""
        return self._percentile(95)

    @property
    def p99(self) -> float:
        """99th percentile latency in ms."""
        return self._percentile(99)

    @property
    def mean(self) -> float:
        """Mean latency in ms."""
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def stdev(self) -> float:
        """Standard deviation of latency in ms."""
        return statistics.stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0

    def _percentile(self, p: int) -> float:
        """Calculate percentile."""
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * p / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "allowed_requests": self.allowed_requests,
            "blocked_requests": self.blocked_requests,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "throughput_rps": round(self.throughput, 2),
            "latency_ms": {
                "mean": round(self.mean, 2),
                "stdev": round(self.stdev, 2),
                "p50": round(self.p50, 2),
                "p95": round(self.p95, 2),
                "p99": round(self.p99, 2),
                "min": round(min(self.latencies_ms), 2) if self.latencies_ms else 0,
                "max": round(max(self.latencies_ms), 2) if self.latencies_ms else 0,
            },
        }


async def setup_policy(client: httpx.AsyncClient, base_url: str, tenant_id: str) -> None:
    """Create a test policy."""
    policy = {
        "tenantId": tenant_id,
        "scope": "TENANT",
        "algorithm": "SLIDING_WINDOW",
        "limit": 10000,  # High limit for benchmarking
        "windowSeconds": 60,
        "burst": 1000,
    }
    await client.post(f"{base_url}/policies", json=policy)


async def evaluate_request(
    client: httpx.AsyncClient, base_url: str, tenant_id: str, route: str
) -> tuple[float, bool, bool]:
    """
    Make a single evaluate request.

    Returns: (latency_ms, success, allowed)
    """
    payload = {"tenantId": tenant_id, "route": route}

    start = time.perf_counter()
    try:
        response = await client.post(f"{base_url}/evaluate", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            return latency_ms, True, data.get("allow", False)
        return latency_ms, False, False
    except Exception:
        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms, False, False


async def benchmark_sequential(
    base_url: str, tenant_id: str, route: str, num_requests: int
) -> BenchmarkResult:
    """Run sequential (mono-client) benchmark."""
    print(f"\n🔄 Sequential benchmark: {num_requests} requests...")

    latencies: list[float] = []
    successful = 0
    allowed = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        await setup_policy(client, base_url, tenant_id)

        start_time = time.perf_counter()

        for i in range(num_requests):
            latency_ms, success, is_allowed = await evaluate_request(
                client, base_url, tenant_id, route
            )
            latencies.append(latency_ms)
            if success:
                successful += 1
            if is_allowed:
                allowed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{num_requests}")

        total_duration = time.perf_counter() - start_time

    return BenchmarkResult(
        total_requests=num_requests,
        successful_requests=successful,
        failed_requests=num_requests - successful,
        allowed_requests=allowed,
        blocked_requests=successful - allowed,
        total_duration_seconds=total_duration,
        latencies_ms=latencies,
    )


async def benchmark_concurrent(
    base_url: str,
    tenant_id: str,
    route: str,
    num_requests: int,
    concurrency: int,
) -> BenchmarkResult:
    """Run concurrent (multi-client) benchmark."""
    print(f"\n⚡ Concurrent benchmark: {num_requests} requests, {concurrency} workers...")

    latencies: list[float] = []
    successful = 0
    allowed = 0
    lock = asyncio.Lock()

    async def worker(
        client: httpx.AsyncClient, semaphore: asyncio.Semaphore, request_queue: asyncio.Queue
    ) -> None:
        nonlocal successful, allowed
        while True:
            try:
                _ = request_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            async with semaphore:
                latency_ms, success, is_allowed = await evaluate_request(
                    client, base_url, tenant_id, route
                )
                async with lock:
                    latencies.append(latency_ms)
                    if success:
                        successful += 1
                    if is_allowed:
                        allowed += 1

    async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=concurrency)) as client:
        await setup_policy(client, base_url, tenant_id)

        # Create request queue
        request_queue: asyncio.Queue[int] = asyncio.Queue()
        for i in range(num_requests):
            await request_queue.put(i)

        semaphore = asyncio.Semaphore(concurrency)

        start_time = time.perf_counter()

        # Create worker tasks
        workers = [
            asyncio.create_task(worker(client, semaphore, request_queue))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)

        total_duration = time.perf_counter() - start_time

    return BenchmarkResult(
        total_requests=num_requests,
        successful_requests=successful,
        failed_requests=num_requests - successful,
        allowed_requests=allowed,
        blocked_requests=successful - allowed,
        total_duration_seconds=total_duration,
        latencies_ms=latencies,
    )


def print_results(result: BenchmarkResult, title: str) -> None:
    """Print benchmark results in a formatted table."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(f"  Total requests:      {result.total_requests:,}")
    print(f"  Successful:          {result.successful_requests:,}")
    print(f"  Failed:              {result.failed_requests:,}")
    print(f"  Allowed:             {result.allowed_requests:,}")
    print(f"  Blocked:             {result.blocked_requests:,}")
    print(f"  Duration:            {result.total_duration_seconds:.2f}s")
    print(f"  Throughput:          {result.throughput:,.2f} req/s")
    print()
    print("  Latency (ms):")
    print(f"    Mean:              {result.mean:.2f}")
    print(f"    Std Dev:           {result.stdev:.2f}")
    print(f"    P50:               {result.p50:.2f}")
    print(f"    P95:               {result.p95:.2f}")
    print(f"    P99:               {result.p99:.2f}")
    print(f"    Min:               {min(result.latencies_ms):.2f}")
    print(f"    Max:               {max(result.latencies_ms):.2f}")
    print(f"{'=' * 60}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="ThrottleX Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="ThrottleX URL")
    parser.add_argument("--tenant", default="t-bench-01", help="Tenant ID")
    parser.add_argument("--route", default="/api/benchmark", help="Route to test")
    parser.add_argument("--requests", type=int, default=1000, help="Number of requests")
    parser.add_argument("--concurrent", type=int, default=0, help="Concurrency (0 = sequential)")
    parser.add_argument("--output", help="Output JSON file")

    args = parser.parse_args()

    print(f"🚀 ThrottleX Benchmark")
    print(f"   URL: {args.url}")
    print(f"   Tenant: {args.tenant}")
    print(f"   Requests: {args.requests}")

    results = {}

    if args.concurrent > 0:
        result = await benchmark_concurrent(
            args.url, args.tenant, args.route, args.requests, args.concurrent
        )
        print_results(result, f"Concurrent ({args.concurrent} workers)")
        results["concurrent"] = result.to_dict()
    else:
        result = await benchmark_sequential(args.url, args.tenant, args.route, args.requests)
        print_results(result, "Sequential (mono-client)")
        results["sequential"] = result.to_dict()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
