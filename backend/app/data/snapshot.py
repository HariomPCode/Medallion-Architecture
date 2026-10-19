"""
backend/app/data/snapshot.py
----------------------------
Immutable in-memory data snapshot and atomic SnapshotManager (§965).
Enforces last-known-good refresh semantics, timestamp skew detection, and thread-safe swaps.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import pandas as pd

from app.core.config import Settings, get_settings
from app.core.errors import DataSourceError
from app.data.contracts import (
    GOLD_ANOMALY_CONTRACT,
    GOLD_CATEGORY_CONTRACT,
    GOLD_DQ_REPORT_CONTRACT,
    GOLD_DQ_RUN_CONTRACT,
    GOLD_TREND_CONTRACT,
)
from app.data.loader import load_gold_table, load_product_reference, load_silver_complaints
from app.data.sources import AzureBlobSource, DataSource, LocalSource, SourceMeta

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    """Immutable container holding typed dataframes and metadata loaded in memory."""

    silver_complaints: pd.DataFrame
    product_reference: pd.DataFrame
    gold_category: pd.DataFrame
    gold_trend: pd.DataFrame
    gold_anomaly: pd.DataFrame
    gold_dq_report: pd.DataFrame
    gold_dq_run: pd.DataFrame | None
    provenance: dict[str, Any]
    loaded_at: str
    skew_warning: bool
    etags: dict[str, str] = field(default_factory=dict)


class SnapshotManager:
    """Manages the in-memory snapshot with atomic swap and last-known-good failure semantics."""

    def __init__(self, settings: Settings, source: DataSource | None = None) -> None:
        self.settings = settings
        self.source = source or self._resolve_source(settings)
        self.current_snapshot: Snapshot | None = None
        self.status: Literal["fresh", "stale", "unavailable"] = "unavailable"
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[None] | None = None

    @staticmethod
    def _resolve_source(settings: Settings) -> DataSource:
        if settings.DATA_MODE == "azure":
            return AzureBlobSource(
                account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
                auth_mode=settings.AZURE_AUTH_MODE,
                connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
                max_blob_bytes=settings.MAX_BLOB_BYTES,
            )
        elif settings.DATA_MODE == "local_snapshot":
            return LocalSource(
                base_dir=settings.LOCAL_DATA_DIR,
                max_blob_bytes=settings.MAX_BLOB_BYTES,
            )
        else:
            # Default fixture mode
            fixture_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "tests",
                "fixtures",
                "tiny",
            )
            return LocalSource(
                base_dir=fixture_dir,
                max_blob_bytes=settings.MAX_BLOB_BYTES,
            )

    async def build_snapshot(self) -> Snapshot:
        """Downloads, validates, and constructs a new immutable Snapshot."""
        warnings: list[str] = []
        object_metas: dict[str, SourceMeta] = {}
        etags: dict[str, str] = {}

        # 1. Fetch Product Reference
        ref_bytes, ref_meta = self.source.fetch(self.settings.SILVER_PRODUCTS_BLOB)
        object_metas[self.settings.SILVER_PRODUCTS_BLOB] = ref_meta
        etags[self.settings.SILVER_PRODUCTS_BLOB] = ref_meta.etag
        df_ref = load_product_reference(ref_bytes)

        # 2. Fetch and enrich Silver Complaints
        silver_bytes, silver_meta = self.source.fetch(self.settings.SILVER_COMPLAINTS_BLOB)
        object_metas[self.settings.SILVER_COMPLAINTS_BLOB] = silver_meta
        etags[self.settings.SILVER_COMPLAINTS_BLOB] = silver_meta.etag
        df_silver, silver_warnings = load_silver_complaints(silver_bytes, df_ref)
        warnings.extend(silver_warnings)

        # 3. Fetch Gold Category
        gold_cat_bytes, cat_meta = self.source.fetch(self.settings.GOLD_CATEGORY_BLOB)
        object_metas[self.settings.GOLD_CATEGORY_BLOB] = cat_meta
        etags[self.settings.GOLD_CATEGORY_BLOB] = cat_meta.etag
        df_gold_cat = load_gold_table(gold_cat_bytes, GOLD_CATEGORY_CONTRACT)

        # 4. Fetch Gold Trend
        gold_trend_bytes, trend_meta = self.source.fetch(self.settings.GOLD_TREND_BLOB)
        object_metas[self.settings.GOLD_TREND_BLOB] = trend_meta
        etags[self.settings.GOLD_TREND_BLOB] = trend_meta.etag
        df_gold_trend = load_gold_table(gold_trend_bytes, GOLD_TREND_CONTRACT)

        # 5. Fetch Gold Anomaly
        gold_anom_bytes, anom_meta = self.source.fetch(self.settings.GOLD_ANOMALY_BLOB)
        object_metas[self.settings.GOLD_ANOMALY_BLOB] = anom_meta
        etags[self.settings.GOLD_ANOMALY_BLOB] = anom_meta.etag
        df_gold_anom = load_gold_table(gold_anom_bytes, GOLD_ANOMALY_CONTRACT)

        # 6. Fetch Gold DQ Report
        gold_dq_bytes, dq_meta = self.source.fetch(self.settings.GOLD_DQ_REPORT_BLOB)
        object_metas[self.settings.GOLD_DQ_REPORT_BLOB] = dq_meta
        etags[self.settings.GOLD_DQ_REPORT_BLOB] = dq_meta.etag
        df_gold_dq = load_gold_table(gold_dq_bytes, GOLD_DQ_REPORT_CONTRACT)

        # 7. Optional Gold DQ Run
        df_gold_run: pd.DataFrame | None = None
        try:
            gold_run_bytes, run_meta = self.source.fetch(self.settings.GOLD_DQ_RUN_BLOB)
            object_metas[self.settings.GOLD_DQ_RUN_BLOB] = run_meta
            etags[self.settings.GOLD_DQ_RUN_BLOB] = run_meta.etag
            df_gold_run = load_gold_table(gold_run_bytes, GOLD_DQ_RUN_CONTRACT)
        except DataSourceError:
            logger.info(
                "Optional DQ run metadata blob '%s' not present; skipping.",
                self.settings.GOLD_DQ_RUN_BLOB,
            )

        # 8. Check timestamp skew across objects
        timestamps = [m.last_modified for m in object_metas.values()]
        skew_warning = False
        if timestamps:
            max_ts = max(timestamps)
            min_ts = min(timestamps)
            diff_hours = (max_ts - min_ts).total_seconds() / 3600.0
            if diff_hours > self.settings.DATA_MAX_SKEW_HOURS:
                skew_warning = True
                msg = (
                    f"Timestamp skew detected: objects differ by {diff_hours:.1f}h "
                    f"(threshold {self.settings.DATA_MAX_SKEW_HOURS}h)"
                )
                warnings.append(msg)
                logger.warning(msg)

        now_iso = datetime.now(timezone.utc).isoformat()
        provenance = {
            "data_origin": self.settings.DATA_MODE,
            "source_description": self.source.describe(),
            "loaded_at": now_iso,
            "warnings": warnings,
            "row_counts": {
                "silver_complaints": len(df_silver),
                "product_reference": len(df_ref),
                "gold_category": len(df_gold_cat),
                "gold_trend": len(df_gold_trend),
                "gold_anomaly": len(df_gold_anom),
            },
        }

        return Snapshot(
            silver_complaints=df_silver,
            product_reference=df_ref,
            gold_category=df_gold_cat,
            gold_trend=df_gold_trend,
            gold_anomaly=df_gold_anom,
            gold_dq_report=df_gold_dq,
            gold_dq_run=df_gold_run,
            provenance=provenance,
            loaded_at=now_iso,
            skew_warning=skew_warning,
            etags=etags,
        )

    async def startup_load(self) -> None:
        """Initial load on application startup."""
        try:
            new_snap = await self.build_snapshot()
            async with self._lock:
                self.current_snapshot = new_snap
                self.status = "fresh"
            logger.info(
                "Initial snapshot loaded successfully (%d complaints, status=fresh)",
                len(new_snap.silver_complaints),
            )
        except Exception as exc:
            logger.error("Snapshot load failed on startup: %s", exc)
            if self.settings.DATA_MODE == "azure":
                # In Azure mode, allow app to start in degraded mode with status=unavailable
                self.status = "unavailable"
            else:
                raise

    async def maybe_refresh(self) -> bool:
        """
        Polls object etags. If any change, builds a new snapshot and swaps atomically.
        On failure, preserves last-known-good snapshot and sets status='stale'.
        """
        if self.current_snapshot is None:
            await self.startup_load()
            return self.current_snapshot is not None

        # Check for etag changes across required objects
        try:
            changed = False
            for blob_name, prev_etag in self.current_snapshot.etags.items():
                try:
                    head_meta = self.source.head(blob_name)
                    if head_meta.etag != prev_etag:
                        changed = True
                        break
                except DataSourceError:
                    changed = True
                    break

            if not changed:
                return False

            logger.info("Changes detected in data source; building new snapshot...")
            new_snapshot = await self.build_snapshot()

            # Atomic swap
            async with self._lock:
                self.current_snapshot = new_snapshot
                self.status = "fresh"

            logger.info(
                "Atomic snapshot refresh succeeded (%d complaints)",
                len(new_snapshot.silver_complaints),
            )
            return True

        except Exception as exc:
            logger.error(
                "Snapshot refresh failed; keeping last-known-good snapshot (status=stale): %s", exc
            )
            async with self._lock:
                self.status = "stale"
            return False

    async def shutdown(self) -> None:
        """Cancels background refresh tasks on shutdown."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()


# Global module singleton instance
_snapshot_manager: SnapshotManager | None = None


def get_snapshot_manager(settings: Settings | None = None) -> SnapshotManager:
    """Singleton getter for SnapshotManager."""
    global _snapshot_manager
    if _snapshot_manager is None:
        app_settings = settings or get_settings()
        _snapshot_manager = SnapshotManager(app_settings)
    return _snapshot_manager


def set_snapshot_manager(manager: SnapshotManager | None) -> None:
    """Helper for testing to inject or reset SnapshotManager."""
    global _snapshot_manager
    _snapshot_manager = manager
