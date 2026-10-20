"""
backend/scripts/loadcheck.py
----------------------------
Lightweight load testing script per §7.3, §1300, and AC-6.5.
Executes 20 concurrent clients, each issuing 200 requests (4,000 total requests) across API endpoints.
Measures p50, p95, max latency, error rate, and verifies zero 5xx errors.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path
from typing import NamedTuple

import httpx
import numpy as np

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class RequestResult(NamedTuple):
    client_id: int
    endpoint: str
    status_code: int
    duration_ms: float
    error: str | None


ENDPOINTS = [
    "/health/live",
    "/api/v1/meta/dataset",
    "/api/v1/meta/filters",
    "/api/v1/dashboard/summary",
    "/api/v1/analytics/by-category",
    "/api/v1/analytics/trends",
    "/api/v1/complaints?page=1&page_size=20",
    "/api/v1/quality/summary",
]


async def client_worker(
    client_id: int,
    client: httpx.AsyncClient,
    requests_to_run: int,
    endpoints: list[str],
    results: list[RequestResult],
    progress: list[int],
    total_target: int,
    start_time: float,
) -> None:
    """Simulates an individual client issuing sequential requests with its own IP identity."""
    headers = {"X-Forwarded-For": f"192.168.1.{client_id}"}
    for _ in range(requests_to_run):
        endpoint = random.choice(endpoints)
        start = time.perf_counter()
        try:
            resp = await client.get(endpoint, headers=headers)
            duration_ms = (time.perf_counter() - start) * 1000.0
            results.append(
                RequestResult(
                    client_id=client_id,
                    endpoint=endpoint,
                    status_code=resp.status_code,
                    duration_ms=duration_ms,
                    error=None if resp.status_code < 500 else f"HTTP {resp.status_code}",
                )
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            results.append(
                RequestResult(
                    client_id=client_id,
                    endpoint=endpoint,
                    status_code=0,
                    duration_ms=duration_ms,
                    error=str(exc),
                )
            )
        progress[0] += 1
        if progress[0] % 500 == 0 or progress[0] == total_target:
            elapsed = time.perf_counter() - start_time
            rate = progress[0] / elapsed if elapsed > 0 else 0
            pct = (progress[0] / total_target) * 100.0
            print(
                f"[{progress[0]:>5}/{total_target} ({pct:5.1f}%)] Elapsed: {elapsed:>6.1f}s | Throughput: {rate:5.1f} req/s"
            )


async def run_load_check(
    base_url: str | None = None,
    concurrency: int = 20,
    requests_per_client: int = 200,
    rate_limit: str = "10000/minute",
) -> int:
    total_requests = concurrency * requests_per_client
    print("=== Finance Complaints Medallion — Load Check (AC-6.5) ===")
    print(f"Concurrency:          {concurrency} clients")
    print(f"Requests per client:  {requests_per_client}")
    print(f"Total Requests:       {total_requests}")

    client: httpx.AsyncClient

    if base_url:
        print(f"Target: Live HTTP server at {base_url}")
        client = httpx.AsyncClient(base_url=base_url, timeout=60.0)
    else:
        print("Target: In-process ASGI transport with local_snapshot data mode")
        from app.core.config import Settings
        from app.main import create_app

        data_dir = backend_dir / ".local_data"
        settings = Settings(
            APP_ENV="test",
            DATA_MODE="local_snapshot" if data_dir.exists() else "fixture",
            LOCAL_DATA_DIR=str(data_dir),
            RATE_LIMIT_DEFAULT=rate_limit,
        )
        app = create_app(settings)
        # Load snapshot before starting benchmark
        from app.data.snapshot import get_snapshot_manager

        manager = get_snapshot_manager(settings)
        await manager.startup_load()

        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0)

    results: list[RequestResult] = []
    progress = [0]
    start_total = time.perf_counter()

    # Launch all client workers concurrently
    tasks = [
        asyncio.create_task(
            client_worker(
                client_id=i + 1,
                client=client,
                requests_to_run=requests_per_client,
                endpoints=ENDPOINTS,
                results=results,
                progress=progress,
                total_target=total_requests,
                start_time=start_total,
            )
        )
        for i in range(concurrency)
    ]

    await asyncio.gather(*tasks)
    await client.aclose()

    total_time_s = time.perf_counter() - start_total
    rps = total_requests / total_time_s if total_time_s > 0 else 0

    durations = [r.duration_ms for r in results]
    successful_requests = [r for r in results if 200 <= r.status_code < 400]
    client_errors = [r for r in results if 400 <= r.status_code < 500]
    server_errors = [r for r in results if r.status_code >= 500 or r.status_code == 0]

    p50 = float(np.percentile(durations, 50))
    p95 = float(np.percentile(durations, 95))
    p99 = float(np.percentile(durations, 99))
    max_lat = max(durations) if durations else 0

    print("\n--- Benchmark Results ---")
    print(f"Total Requests:       {len(results)}/{total_requests}")
    print(f"Successful (2xx/3xx): {len(successful_requests)}")
    print(f"Client Errors (4xx):  {len(client_errors)}")
    print(f"Server Errors (5xx):  {len(server_errors)} (target: 0)")
    print(f"Total Elapsed Time:   {total_time_s:.2f} s")
    print(f"Throughput:           {rps:.1f} req/s")
    print(f"Latency (p50):        {p50:.1f} ms")
    print(f"Latency (p95):        {p95:.1f} ms")
    print(f"Latency (p99):        {p99:.1f} ms")
    print(f"Latency (max):        {max_lat:.1f} ms")

    # Endpoint breakdown
    print("\n--- Endpoint Latency Summary ---")
    for ep in ENDPOINTS:
        ep_results = [r for r in results if r.endpoint == ep]
        if ep_results:
            ep_durations = [r.duration_ms for r in ep_results]
            ep_errs = [r for r in ep_results if r.status_code >= 500 or r.status_code == 0]
            print(
                f"  {ep:<42} | count={len(ep_results):>4} | "
                f"p50={np.percentile(ep_durations, 50):>6.1f} ms | "
                f"p95={np.percentile(ep_durations, 95):>6.1f} ms | "
                f"5xx={len(ep_errs)}"
            )

    if server_errors:
        print(f"\nFAILED: {len(server_errors)} requests encountered server errors (5xx/network):")
        for err in server_errors[:5]:
            print(f"  Client {err.client_id} -> {err.endpoint} -> {err.status_code} ({err.error})")
        return 1

    print(
        f"\nSUCCESS: 0 server errors across all {total_requests:,} requests. AC-6.5 target satisfied."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backend load check per AC-6.5.")
    parser.add_argument("--url", type=str, default=None, help="Base URL of live server")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Number of concurrent clients (default: 20)",
    )
    parser.add_argument(
        "--requests-per-client",
        type=int,
        default=200,
        help="Requests executed per client (default: 200 -> 4,000 total)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=None,
        help="Legacy total requests override (divides by concurrency if given)",
    )
    parser.add_argument(
        "--rate-limit",
        type=str,
        default="10000/minute",
        help="Rate limit configured for in-process load test",
    )
    args = parser.parse_args()

    reqs_per_client = args.requests_per_client
    if args.requests is not None:
        reqs_per_client = max(1, args.requests // args.concurrency)

    exit_code = asyncio.run(
        run_load_check(
            base_url=args.url,
            concurrency=args.concurrency,
            requests_per_client=reqs_per_client,
            rate_limit=args.rate_limit,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
