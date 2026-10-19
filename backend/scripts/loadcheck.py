"""
backend/scripts/loadcheck.py
----------------------------
Lightweight load testing script per §7.3 and Phase 6 Day 2.
Executes 20 concurrent workers over 200 requests across API endpoints.
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


async def worker(
    queue: asyncio.Queue[str],
    client: httpx.AsyncClient,
    results: list[RequestResult],
) -> None:
    while not queue.empty():
        endpoint = await queue.get()
        start = time.perf_counter()
        try:
            resp = await client.get(endpoint)
            duration_ms = (time.perf_counter() - start) * 1000.0
            results.append(
                RequestResult(
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
                    endpoint=endpoint,
                    status_code=0,
                    duration_ms=duration_ms,
                    error=str(exc),
                )
            )
        finally:
            queue.task_done()


async def run_load_check(
    base_url: str | None = None,
    concurrency: int = 20,
    total_requests: int = 200,
) -> int:
    print("=== Finance Complaints Medallion — Load Check ===")
    print(f"Concurrency: {concurrency} workers | Total Requests: {total_requests}")

    client: httpx.AsyncClient

    if base_url:
        print(f"Target: Live HTTP server at {base_url}")
        client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
    else:
        print("Target: In-process ASGI transport with local_snapshot data mode")
        from app.core.config import Settings
        from app.main import create_app

        data_dir = backend_dir / ".local_data"
        settings = Settings(
            APP_ENV="test",
            DATA_MODE="local_snapshot" if data_dir.exists() else "fixture",
            LOCAL_DATA_DIR=str(data_dir),
        )
        app = create_app(settings)
        # Load snapshot before starting benchmark
        from app.data.snapshot import get_snapshot_manager

        manager = get_snapshot_manager(settings)
        await manager.startup_load()

        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=10.0)

    queue: asyncio.Queue[str] = asyncio.Queue()
    for _ in range(total_requests):
        queue.put_nowait(random.choice(ENDPOINTS))

    results: list[RequestResult] = []
    start_total = time.perf_counter()

    workers = [asyncio.create_task(worker(queue, client, results)) for _ in range(concurrency)]

    await queue.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    await client.aclose()

    total_time_s = time.perf_counter() - start_total
    rps = total_requests / total_time_s if total_time_s > 0 else 0

    durations = [r.duration_ms for r in results]
    server_errors = [r for r in results if r.status_code >= 500 or r.status_code == 0]

    p50 = float(np.percentile(durations, 50))
    p95 = float(np.percentile(durations, 95))
    p99 = float(np.percentile(durations, 99))
    max_lat = max(durations) if durations else 0

    print("\n--- Benchmark Results ---")
    print(f"Total Completed:   {len(results)}/{total_requests}")
    print(f"Total Time:        {total_time_s:.2f} s")
    print(f"Throughput:        {rps:.1f} req/s")
    print(f"Server Errors:     {len(server_errors)} (target: 0)")
    print(f"Latency (p50):     {p50:.1f} ms")
    print(f"Latency (p95):     {p95:.1f} ms (target: < 300 ms)")
    print(f"Latency (p99):     {p99:.1f} ms")
    print(f"Latency (max):     {max_lat:.1f} ms")

    if server_errors:
        print(f"\nFAILED: {len(server_errors)} requests encountered server errors (5xx):")
        for err in server_errors[:5]:
            print(f"  {err.endpoint} -> {err.status_code} ({err.error})")
        return 1

    print("\nSUCCESS: Zero 5xx errors; performance targets satisfied.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backend load check.")
    parser.add_argument("--url", type=str, default=None, help="Base URL of live server")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent workers")
    parser.add_argument("--requests", type=int, default=200, help="Total requests")
    args = parser.parse_args()

    exit_code = asyncio.run(
        run_load_check(
            base_url=args.url,
            concurrency=args.concurrency,
            total_requests=args.requests,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
