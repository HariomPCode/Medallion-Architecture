"""
backend/app/data/sources.py
---------------------------
Data source abstraction protocol and concrete implementations (§964, §978).
Provides LocalSource for offline fixtures/snapshots and AzureBlobSource for cloud ingestion.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.core.errors import DataSourceError


@dataclass(frozen=True)
class SourceMeta:
    """Metadata describing a data source object."""

    name: str
    etag: str
    last_modified: datetime
    size_bytes: int


@runtime_checkable
class DataSource(Protocol):
    """Protocol defining the data source interface for Medallion pipeline assets."""

    def describe(self) -> str:
        """Returns human-readable description of the data source and location."""
        ...

    def head(self, name: str) -> SourceMeta:
        """Retrieves metadata for an object without downloading content."""
        ...

    def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
        """Downloads and returns raw bytes and metadata for an object."""
        ...


class LocalSource:
    """File-system based data source for local snapshots and test fixtures."""

    def __init__(self, base_dir: str, max_blob_bytes: int = 104_857_600) -> None:
        self.base_dir = base_dir
        self.max_blob_bytes = max_blob_bytes

    def describe(self) -> str:
        return f"LocalSource(base_dir='{self.base_dir}')"

    def _resolve_path(self, name: str) -> str:
        # Check direct path, then silver/ and gold/ subdirectories
        candidates = [
            os.path.join(self.base_dir, name),
            os.path.join(self.base_dir, "silver", name),
            os.path.join(self.base_dir, "gold", name),
        ]
        for p in candidates:
            if os.path.exists(p) and os.path.isfile(p):
                return p
        raise DataSourceError(f"Object '{name}' not found in '{self.base_dir}'")

    def head(self, name: str) -> SourceMeta:
        path = self._resolve_path(name)
        stat = os.stat(path)
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        # Deterministic etag based on mtime and size
        etag = f"{int(stat.st_mtime)}-{stat.st_size}"
        return SourceMeta(name=name, etag=etag, last_modified=mtime, size_bytes=stat.st_size)

    def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
        path = self._resolve_path(name)
        meta = self.head(name)

        if meta.size_bytes > self.max_blob_bytes:
            raise DataSourceError(
                f"Object '{name}' size ({meta.size_bytes} bytes) exceeds MAX_BLOB_BYTES ({self.max_blob_bytes})"
            )

        try:
            with open(path, "rb") as f:
                content = f.read()
            return content, meta
        except Exception as exc:
            raise DataSourceError(f"Failed to read local object '{name}': {exc}") from exc


class AzureBlobSource:
    """
    Azure Data Lake Storage Gen2 blob data source (§978).
    Connects via DefaultAzureCredential or connection string (local dev only).
    """

    def __init__(
        self,
        account_name: str,
        auth_mode: str = "default_credential",
        connection_string: str = "",
        max_blob_bytes: int = 104_857_600,
        blob_service_client: object | None = None,
    ) -> None:
        self.account_name = account_name
        self.auth_mode = auth_mode
        self.connection_string = connection_string
        self.max_blob_bytes = max_blob_bytes
        self._client = blob_service_client

    def describe(self) -> str:
        return f"AzureBlobSource(account='{self.account_name}', auth_mode='{self.auth_mode}')"

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client

        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise DataSourceError("azure-storage-blob library is not installed") from exc

        try:
            if self.auth_mode == "connection_string" and self.connection_string:
                self._client = BlobServiceClient.from_connection_string(self.connection_string)
            else:
                from azure.identity import DefaultAzureCredential

                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(
                    account_url=account_url, credential=DefaultAzureCredential()
                )
            return self._client
        except Exception as exc:
            # Sanitize error message to prevent leaking any secrets
            raise DataSourceError(
                f"Failed to initialize Azure Blob client: {type(exc).__name__}"
            ) from exc

    def _get_blob_client(self, name: str) -> object:
        client = self._get_client()
        # Derive container: silver if ConsumerComplaints/Product, else gold
        container = "silver" if ("Silver" in name or "ProductCategory" in name) else "gold"
        try:
            return getattr(client, "get_blob_client")(container=container, blob=name)
        except Exception as exc:
            raise DataSourceError(
                f"Failed to get blob client for '{name}': {type(exc).__name__}"
            ) from exc

    def head(self, name: str) -> SourceMeta:
        blob_client = self._get_blob_client(name)
        try:
            props = getattr(blob_client, "get_blob_properties")()
            mtime = props.last_modified
            if mtime.tzinfo is None:
                mtime = mtime.replace(tzinfo=timezone.utc)
            return SourceMeta(
                name=name,
                etag=props.etag.strip('"'),
                last_modified=mtime,
                size_bytes=props.size,
            )
        except Exception as exc:
            err_name = type(exc).__name__
            if "ResourceNotFound" in err_name:
                raise DataSourceError(f"Blob '{name}' not found in storage account") from exc
            if "ClientAuthentication" in err_name:
                raise DataSourceError(
                    f"Authentication failed for storage account: {err_name}"
                ) from exc
            raise DataSourceError(
                f"Failed to retrieve metadata for blob '{name}': {err_name}"
            ) from exc

    def fetch(self, name: str) -> tuple[bytes, SourceMeta]:
        meta = self.head(name)
        if meta.size_bytes > self.max_blob_bytes:
            raise DataSourceError(
                f"Blob '{name}' size ({meta.size_bytes} bytes) exceeds MAX_BLOB_BYTES ({self.max_blob_bytes})"
            )

        blob_client = self._get_blob_client(name)
        try:
            downloader = getattr(blob_client, "download_blob")()
            content = downloader.readall()
            return content, meta
        except Exception as exc:
            err_name = type(exc).__name__
            raise DataSourceError(f"Failed to download blob '{name}': {err_name}") from exc
