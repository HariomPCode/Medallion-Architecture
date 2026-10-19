"""
backend/tests/integration/test_contract.py
------------------------------------------
Contract snapshot test per §13 and Phase 6 Day 3 & Day 4.

Asserts that the running application's OpenAPI schema exactly matches the
committed contract in `docs/openapi.json`. Fails if any endpoint, path,
parameter, or schema diverges without explicitly re-exporting the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_openapi_contract_snapshot_exact_match():
    """
    AC-6.6: docs/openapi.json committed, matches the running app, contract test enforces it.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    contract_file = repo_root / "docs" / "openapi.json"

    assert contract_file.exists(), f"Committed OpenAPI contract file missing: {contract_file}"

    with open(contract_file, "r", encoding="utf-8") as f:
        committed_schema = json.load(f)

    # Instantiate test application to inspect generated OpenAPI schema
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)
    running_schema = app.openapi()

    # Compare keys, paths, and components
    assert running_schema == committed_schema, (
        "OpenAPI contract drift detected! The running application's OpenAPI specification "
        "does not match 'docs/openapi.json'.\n"
        "If pre-freeze changes were authorized, regenerate via: "
        "'python backend/scripts/export_openapi.py' and commit the updated contract."
    )
