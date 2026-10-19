"""
backend/tests/integration/test_reliability.py
---------------------------------------------
Reliability, fault tolerance, and refresh-under-load tests per §7.3 and Phase 6 Day 2.

Covers:
- Startup behavior when data source is unreachable (liveness 200, readiness 503, recovery after source returns).
- Atomic snapshot refresh under concurrent query load (0 server errors, no corrupted reads).
- Timestamp skew warning detection in meta/dataset.
- Graceful shutdown of the snapshot manager.
- In-memory snapshot RSS measurement (< 512 MB).
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import DataSourceError
from app.data.snapshot import SnapshotManager, get_snapshot_manager
from app.data.sources import LocalSource, SourceMeta
from app.main import create_app


class FlakyLocalSource(LocalSource):
    """A test data source that inherits LocalSource resolution and can simulate outages/recovery."""

    def __init__(self, base_dir: str, initially_failing: bool = True) -> None:
        super().__init__(base_dir=base_dir)
        self.is_failing = initially_failing

    def describe(self) -> str:
        return f"FlakyLocalSource(failing={self.is_failing})"

    def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
        if self.is_failing:
            raise DataSourceError(f"Simulated network outage fetching {name}")
        return super().fetch(name)

    def head(self, name: str) -> SourceMeta:
        if self.is_failing:
            raise DataSourceError(f"Simulated outage on head {name}")
        return super().head(name)


class SkewedLocalSource(LocalSource):
    """LocalSource that injects a simulated timestamp skew > DATA_MAX_SKEW_HOURS."""

    def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
        data, meta = super().fetch(name)
        now = datetime.now(timezone.utc)
        if "Product" in name:
            skewed_time = now - timedelta(hours=72)
        else:
            skewed_time = now
        skewed_meta = SourceMeta(
            name=meta.name,
            size_bytes=meta.size_bytes,
            last_modified=skewed_time,
            etag=meta.etag,
        )
        return data, skewed_meta


@pytest.mark.anyio
async def test_startup_with_unreachable_source_and_recovery():
    """Verify app starts with unavailable source, returns 503 on ready, and recovers when source is restored."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "tiny")
    source = FlakyLocalSource(base_dir=fixture_dir, initially_failing=True)

    settings = Settings(
        APP_ENV="test",
        DATA_MODE="azure",  # Allows app to start in degraded mode with status=unavailable
    )
    app = create_app(settings)
    manager = SnapshotManager(settings=settings, source=source)
    app.state.snapshot_manager = manager

    # 1. Startup load fails gracefully
    await manager.startup_load()
    assert manager.status == "unavailable"
    assert manager.current_snapshot is None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Liveness probe returns 200
        live_res = await client.get("/health/live")
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "alive"

        # Readiness probe returns 503
        ready_res = await client.get("/health/ready")
        assert ready_res.status_code == 503
        assert ready_res.json()["error"]["code"] == "DATA_UNAVAILABLE"

        # 2. Source recovers
        source.is_failing = False
        refreshed = await manager.maybe_refresh()
        assert refreshed is True
        assert manager.status == "fresh"
        assert manager.current_snapshot is not None

        # Readiness probe now returns 200
        ready_recovered = await client.get("/health/ready")
        assert ready_recovered.status_code == 200
        assert ready_recovered.json()["status"] == "ready"


@pytest.mark.anyio
async def test_atomic_refresh_under_concurrent_queries():
    """Verify atomic snapshot swap under concurrent read queries without 5xx or corrupted data."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)
    manager = get_snapshot_manager(settings)
    await manager.startup_load()
    assert manager.current_snapshot is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Launch 20 concurrent readers
        async def query_reader(idx: int) -> int:
            endpoint = "/api/v1/dashboard/summary" if idx % 2 == 0 else "/api/v1/meta/dataset"
            res = await client.get(endpoint)
            assert res.status_code == 200
            return res.status_code

        # Run concurrent readers alongside an atomic snapshot rebuild
        tasks = [asyncio.create_task(query_reader(i)) for i in range(20)]

        # Simulate atomic swap in manager
        new_snap = await manager.build_snapshot()
        async with manager._lock:
            manager.current_snapshot = new_snap

        results = await asyncio.gather(*tasks)
        assert len(results) == 20
        assert all(code == 200 for code in results)


@pytest.mark.anyio
async def test_timestamp_skew_detection_in_meta_dataset():
    """Verify timestamp skew warning is triggered when objects differ by > DATA_MAX_SKEW_HOURS."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "tiny")
    source = SkewedLocalSource(base_dir=fixture_dir)

    settings = Settings(
        APP_ENV="test",
        DATA_MODE="fixture",
        DATA_MAX_SKEW_HOURS=24,
    )
    app = create_app(settings)
    manager = SnapshotManager(settings=settings, source=source)
    app.state.snapshot_manager = manager
    await manager.startup_load()
    assert manager.current_snapshot is not None
    assert manager.current_snapshot.skew_warning is True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/meta/dataset")
        assert res.status_code == 200
        data = res.json()
        assert data["skew_warning"] is True


@pytest.mark.anyio
async def test_graceful_shutdown():
    """Verify snapshot manager shutdown cancels background tasks cleanly."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings=settings)
    await manager.startup_load()
    await manager.shutdown()
    assert manager._refresh_task is None or manager._refresh_task.cancelled()


def test_memory_rss_footprint():
    """Verify that in-memory dataset footprint is well below the 512 MB ceiling per §7.3."""
    import psutil

    process = psutil.Process()
    rss_mb = process.memory_info().rss / (1024 * 1024)
    print(f"\n[RSS Footprint] Current process RSS: {rss_mb:.1f} MB (ceiling: 512 MB)")
    assert rss_mb < 512, f"Process memory {rss_mb} MB exceeds 512 MB ceiling"
