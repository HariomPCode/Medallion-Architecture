"""
backend/tests/unit/test_complaints.py
-------------------------------------
Unit tests for Complaint Explorer domain operations (§13.2 #9, #10, #11).
Tests filtering, deterministic sorting with tie-break, pagination, detail lookup,
CSV export streaming, and formula-injection guards.
"""

import pytest

from app.core.config import Settings
from app.core.errors import NotFoundException, ValidationException
from app.data.snapshot import SnapshotManager
from app.domain.complaints import (
    EXPORT_CSV_COLUMNS,
    get_complaint_detail,
    sanitize_csv_cell,
    search_complaints,
    stream_complaints_csv,
    validate_complaint_id_query,
)
from app.domain.filters import ComplaintFilters


@pytest.fixture
def tiny_snapshot():
    settings = Settings(DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    import asyncio

    return asyncio.run(manager.build_snapshot())


def test_sanitize_csv_cell_injection_guard():
    """Formulas beginning with =, +, -, @, \\t, \\r must be prefixed with a single quote."""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_cell("+cmd|'/c calc'!A0") == "'+cmd|'/c calc'!A0"
    assert sanitize_csv_cell("-10+20") == "'-10+20"
    assert sanitize_csv_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_csv_cell("\ttab_prefix") == "'\ttab_prefix"
    assert sanitize_csv_cell("\rreturn_prefix") == "'\rreturn_prefix"

    # Non-formula strings and other types remain untouched
    assert sanitize_csv_cell("Regular text") == "Regular text"
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell(12345) == 12345
    assert sanitize_csv_cell(None) is None


def test_validate_complaint_id_query():
    """'q' search query must validate to numeric ID <= 12 characters."""
    assert validate_complaint_id_query(None) is None
    assert validate_complaint_id_query("") is None
    assert validate_complaint_id_query("  1234567  ") == 1234567

    # Non-numeric string
    with pytest.raises(ValidationException) as exc:
        validate_complaint_id_query("abc123")
    assert "digits only" in str(exc.value)

    # String longer than 12 digits
    with pytest.raises(ValidationException) as exc:
        validate_complaint_id_query("1234567890123")
    assert "up to 12 characters" in str(exc.value)


def test_search_complaints_pagination(tiny_snapshot):
    """Pagination must respect page boundaries and return correct total_pages."""
    filters = ComplaintFilters()
    total = len(tiny_snapshot.silver_complaints)

    # Page 1 with page_size=2
    res = search_complaints(tiny_snapshot, filters, page=1, page_size=2)
    assert res.total == total
    assert len(res.items) == min(2, total)
    assert res.page == 1
    assert res.page_size == 2

    # Beyond last page
    res_beyond = search_complaints(tiny_snapshot, filters, page=999, page_size=2)
    assert res_beyond.total == total
    assert res_beyond.items == []

    # Invalid page numbers
    with pytest.raises(ValidationException):
        search_complaints(tiny_snapshot, filters, page=0)

    # Invalid page sizes
    with pytest.raises(ValidationException):
        search_complaints(tiny_snapshot, filters, page_size=0)
    with pytest.raises(ValidationException):
        search_complaints(tiny_snapshot, filters, page_size=101)


def test_search_complaints_sorting(tiny_snapshot):
    """Sorting must support whitelisted columns and stable Complaint_ID tie-breaks."""
    filters = ComplaintFilters()

    # Valid sorts
    res_desc = search_complaints(tiny_snapshot, filters, sort_by="complaint_id", sort_dir="desc")
    ids_desc = [item.complaint_id for item in res_desc.items]
    assert ids_desc == sorted(ids_desc, reverse=True)

    res_asc = search_complaints(tiny_snapshot, filters, sort_by="complaint_id", sort_dir="asc")
    ids_asc = [item.complaint_id for item in res_asc.items]
    assert ids_asc == sorted(ids_asc)

    # Invalid sort column
    with pytest.raises(ValidationException) as exc:
        search_complaints(tiny_snapshot, filters, sort_by="unsupported_column")
    assert "Invalid sort column" in str(exc.value)

    # Invalid sort direction
    with pytest.raises(ValidationException) as exc:
        search_complaints(tiny_snapshot, filters, sort_dir="invalid")
    assert "Invalid sort direction" in str(exc.value)


def test_get_complaint_detail(tiny_snapshot):
    """Detail lookup returns whitelisted fields for existing ID, raises 404 for missing ID."""
    first_id = int(tiny_snapshot.silver_complaints["Complaint_ID"].iloc[0])
    detail = get_complaint_detail(tiny_snapshot, first_id)

    assert detail.complaint_id == first_id
    assert detail.category is not None
    assert detail.product is not None
    assert detail.issue is not None

    # Missing ID raises 404
    with pytest.raises(NotFoundException) as exc:
        get_complaint_detail(tiny_snapshot, 999_999_999)
    assert "was not found" in str(exc.value)


def test_stream_complaints_csv(tiny_snapshot):
    """CSV export generator yields headers, respects capping, and applies injection guard."""
    filters = ComplaintFilters()
    gen, count, is_truncated = stream_complaints_csv(tiny_snapshot, filters, max_rows=2)

    total = len(tiny_snapshot.silver_complaints)
    assert count == min(2, total)
    assert is_truncated == (total > 2)

    chunks = list(gen)
    header_line = chunks[0].strip()
    assert header_line == ",".join(EXPORT_CSV_COLUMNS)
    assert len(chunks) == count + 1  # 1 header + count rows
