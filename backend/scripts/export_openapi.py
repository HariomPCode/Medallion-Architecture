#!/usr/bin/env python3
"""
backend/scripts/export_openapi.py
---------------------------------
Exports the FastAPI application OpenAPI 3.1 JSON schema to docs/openapi.json (§1072).
"""

import json
import os
import sys

# Ensure backend root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def export_openapi(output_path: str) -> None:
    # Use test env settings to avoid requiring live Azure connections
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)
    openapi_schema = app.openapi()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {output_path} ({len(json.dumps(openapi_schema))} bytes)")


if __name__ == "__main__":
    repo_root = os.path.dirname(backend_root)
    target = os.path.join(repo_root, "docs", "openapi.json")
    export_openapi(target)
