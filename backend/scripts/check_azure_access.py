#!/usr/bin/env python3
"""
backend/scripts/check_azure_access.py
-------------------------------------
Probes Azure Data Lake Storage Gen2 for required Silver and Gold Medallion blobs (§979).
Reports blob existence, byte size, and last-modified timestamps.
NEVER logs or outputs storage keys, connection strings, or authorization tokens.

Exits with code 0 if all required blobs are accessible, 1 otherwise.
"""

import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.errors import DataSourceError
from app.data.sources import AzureBlobSource


def check_azure() -> int:
    settings = get_settings()

    print("=" * 70)
    print("AZURE DATA LAKE STORAGE GEN2 ACCESS CHECK")
    print("=" * 70)
    print(f"Target Storage Account : {settings.AZURE_STORAGE_ACCOUNT_NAME}")
    print(f"Auth Mode              : {settings.AZURE_AUTH_MODE}")
    print(f"Silver Container       : {settings.AZURE_SILVER_CONTAINER}")
    print(f"Gold Container         : {settings.AZURE_GOLD_CONTAINER}")
    print("-" * 70)

    source = AzureBlobSource(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        auth_mode=settings.AZURE_AUTH_MODE,
        connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
        max_blob_bytes=settings.MAX_BLOB_BYTES,
    )

    required_blobs = [
        settings.SILVER_COMPLAINTS_BLOB,
        settings.SILVER_PRODUCTS_BLOB,
        settings.GOLD_CATEGORY_BLOB,
        settings.GOLD_TREND_BLOB,
        settings.GOLD_ANOMALY_BLOB,
        settings.GOLD_DQ_REPORT_BLOB,
    ]

    optional_blobs = [
        settings.GOLD_DQ_RUN_BLOB,
    ]

    failures = []
    print("\nProbing Required Medallion Blobs...")
    for blob in required_blobs:
        try:
            meta = source.head(blob)
            print(
                f"  [OK] {blob:35} | {meta.size_bytes:>10,} bytes | Modified: {meta.last_modified}"
            )
        except DataSourceError as exc:
            print(f"  [FAIL] {blob:33} | Error: {exc.message}")
            failures.append((blob, exc.message))
        except Exception as exc:
            print(f"  [FAIL] {blob:33} | Unexpected error: {type(exc).__name__}")
            failures.append((blob, str(exc)))

    print("\nProbing Optional Blobs...")
    for blob in optional_blobs:
        try:
            meta = source.head(blob)
            print(
                f"  [OK] {blob:35} | {meta.size_bytes:>10,} bytes | Modified: {meta.last_modified}"
            )
        except Exception:
            print(f"  [SKIP] {blob:33} | Optional blob not published")

    print("\n" + "=" * 70)
    if failures:
        print(f"AZURE ACCESS CHECK FAILED ({len(failures)} required blobs inaccessible)")
        print("\nTroubleshooting instructions for project team:")
        print("1. Ensure Azure CLI is logged in: 'az login'")
        print(
            "2. Ensure App Service managed identity or user identity has 'Storage Blob Data Reader' role"
        )
        print(
            "   on resource: /subscriptions/.../storageAccounts/"
            + settings.AZURE_STORAGE_ACCOUNT_NAME
        )
        print(
            "3. Alternatively, for local testing, set AZURE_STORAGE_CONNECTION_STRING in backend/.env"
        )
        print("=" * 70)
        return 1

    print("AZURE ACCESS SUCCESS: ALL REQUIRED BLOBS ACCESSIBLE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(check_azure())
