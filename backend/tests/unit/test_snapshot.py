"""
backend/tests/unit/test_snapshot.py
-----------------------------------
Unit tests for SnapshotManager, atomic swaps, and last-known-good failure semantics (§968).
"""

import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import DataSourceError
from app.data.snapshot import SnapshotManager, set_snapshot_manager
from app.data.sources import LocalSource, SourceMeta
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the global snapshot manager before each test."""
    set_snapshot_manager(None)
    yield
    set_snapshot_manager(None)


@pytest.mark.anyio
async def test_snapshot_loads_tiny_fixture_successfully():
    """Verify loading from tests/fixtures/tiny constructs valid snapshot and sets status='fresh'."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    await manager.startup_load()

    assert manager.status == "fresh"
    assert manager.current_snapshot is not None
    assert len(manager.current_snapshot.silver_complaints) == 40
    assert len(manager.current_snapshot.product_reference) == 9
    assert len(manager.current_snapshot.gold_category) == 7
    assert manager.current_snapshot.provenance["data_origin"] == "fixture"


@pytest.mark.anyio
async def test_health_ready_with_loaded_snapshot():
    """GET /health/ready returns 200 with data_status, row count, and provenance."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    await manager.startup_load()
    set_snapshot_manager(manager)

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["data_status"] == "fresh"
        assert data["row_count"] == 40
        assert data["data_origin"] == "fixture"


@pytest.mark.anyio
async def test_health_ready_returns_503_when_unavailable():
    """GET /health/ready returns 503 when no validated snapshot is loaded."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    set_snapshot_manager(manager)

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "DATA_UNAVAILABLE"


@pytest.mark.anyio
async def test_failed_refresh_keeps_last_known_good_snapshot():
    """When refresh fails, old snapshot is preserved and status is marked 'stale'."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    await manager.startup_load()
    assert manager.status == "fresh"
    initial_snap = manager.current_snapshot

    # Mock source head/fetch to induce a failure during refresh
    class FailingSource(LocalSource):
        def head(self, name: str) -> SourceMeta:
            # Report a different etag to trigger refresh
            return SourceMeta(
                name=name,
                etag="new-different-etag",
                last_modified=datetime.now(timezone.utc),
                size_bytes=100,
            )

        def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
            raise DataSourceError("Simulated network outage during blob download")

    manager.source = FailingSource(base_dir="tests/fixtures/tiny")
    refreshed = await manager.maybe_refresh()

    assert refreshed is False
    assert manager.status == "stale"
    assert manager.current_snapshot is initial_snap  # old snapshot preserved intact!


@pytest.mark.anyio
async def test_oversize_blob_is_rejected():
    """Blob exceeding MAX_BLOB_BYTES is rejected by data source."""
    fixture_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "tiny")
    source = LocalSource(base_dir=fixture_dir, max_blob_bytes=50)  # artificially low limit

    with pytest.raises(DataSourceError, match="exceeds MAX_BLOB_BYTES"):
        source.fetch("ConsumerComplaints_Silver.csv")
