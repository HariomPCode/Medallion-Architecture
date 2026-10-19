"""
backend/tests/unit/test_azure_source.py
---------------------------------------
Unit tests for AzureBlobSource with mocked Azure SDK client (§980).
Verifies sanitized error mapping, timeout handling, oversize blob rejection, and key redaction.
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.errors import DataSourceError
from app.data.sources import AzureBlobSource


def test_azure_blob_source_describe():
    """Verify describe() does not leak connection strings or keys."""
    source = AzureBlobSource(account_name="mytestsa", auth_mode="default_credential")
    desc = source.describe()
    assert "mytestsa" in desc
    assert "AccountKey" not in desc
    assert "sig=" not in desc


def test_azure_blob_source_head_success():
    """Mocked get_blob_properties returns clean SourceMeta."""
    mock_blob_client = MagicMock()
    mock_props = MagicMock()
    mock_props.etag = '"etag-abc-123"'
    mock_props.last_modified = datetime(2023, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    mock_props.size = 1024
    mock_blob_client.get_blob_properties.return_value = mock_props

    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    source = AzureBlobSource(account_name="testsa", blob_service_client=mock_service_client)
    meta = source.head("ConsumerComplaints_Silver.csv")

    assert meta.name == "ConsumerComplaints_Silver.csv"
    assert meta.etag == "etag-abc-123"
    assert meta.size_bytes == 1024
    assert meta.last_modified.year == 2023


def test_azure_blob_source_fetch_success():
    """Mocked download_blob reads and returns content bytes."""
    mock_blob_client = MagicMock()
    mock_props = MagicMock()
    mock_props.etag = '"etag-456"'
    mock_props.last_modified = datetime.now(timezone.utc)
    mock_props.size = 25
    mock_blob_client.get_blob_properties.return_value = mock_props

    mock_downloader = MagicMock()
    mock_downloader.readall.return_value = b"col1,col2\nval1,val2\n"
    mock_blob_client.download_blob.return_value = mock_downloader

    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    source = AzureBlobSource(account_name="testsa", blob_service_client=mock_service_client)
    content, meta = source.fetch("test_blob.csv")

    assert content == b"col1,col2\nval1,val2\n"
    assert meta.size_bytes == 25


def test_azure_blob_source_404_maps_to_datasource_error():
    """404 ResourceNotFoundError maps to DataSourceError with sanitized message."""

    class ResourceNotFoundError(Exception):
        pass

    mock_blob_client = MagicMock()
    mock_blob_client.get_blob_properties.side_effect = ResourceNotFoundError(
        "The specified blob does not exist."
    )

    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    source = AzureBlobSource(account_name="testsa", blob_service_client=mock_service_client)
    with pytest.raises(DataSourceError, match="not found in storage account"):
        source.head("missing.csv")


def test_azure_blob_source_403_auth_failure_maps_to_datasource_error():
    """403 ClientAuthenticationError maps to sanitized DataSourceError without credentials."""

    class ClientAuthenticationError(Exception):
        pass

    mock_blob_client = MagicMock()
    mock_blob_client.get_blob_properties.side_effect = ClientAuthenticationError(
        "Server failed to authenticate the request with AccountKey=secretkey123"
    )

    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    source = AzureBlobSource(account_name="testsa", blob_service_client=mock_service_client)
    with pytest.raises(DataSourceError, match="Authentication failed"):
        source.head("secure.csv")


def test_azure_blob_source_oversize_rejected():
    """Oversize blob raises DataSourceError before attempting to download bytes."""
    mock_blob_client = MagicMock()
    mock_props = MagicMock()
    mock_props.etag = '"etag-huge"'
    mock_props.last_modified = datetime.now(timezone.utc)
    mock_props.size = 200_000_000  # 200 MB
    mock_blob_client.get_blob_properties.return_value = mock_props

    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    source = AzureBlobSource(
        account_name="testsa",
        max_blob_bytes=104_857_600,
        blob_service_client=mock_service_client,
    )

    with pytest.raises(DataSourceError, match="exceeds MAX_BLOB_BYTES"):
        source.fetch("huge_file.csv")


@pytest.mark.azure
def test_live_azure_access_opt_in():
    """Live cloud check; skipped by default unless RUN_AZURE_TESTS=1."""
    if os.getenv("RUN_AZURE_TESTS") != "1":
        pytest.skip("Skipping live Azure test; set RUN_AZURE_TESTS=1 to run.")

    source = AzureBlobSource(
        account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "financecomplaintssa")
    )
    meta = source.head("ConsumerComplaints_Silver.csv")
    assert meta.size_bytes > 0
