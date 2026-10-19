"""
backend/app/api/deps.py
-----------------------
FastAPI dependencies for data snapshot retrieval and query parameter validation (§13.1 and §1027).
"""

from typing import Callable, Set

from fastapi import Depends, Request

from app.core.errors import DataSourceError, ValidationException
from app.data.snapshot import Snapshot, get_snapshot_manager
from app.domain.filters import ComplaintFilters

COMMON_FILTER_PARAMS: Set[str] = {
    "category",
    "sub_category",
    "submitted_via",
    "state",
    "company_response",
    "timely",
    "issue",
    "date_from",
    "date_to",
}


def get_current_snapshot() -> Snapshot:
    """Retrieves the active immutable Snapshot. Raises 503 DATA_UNAVAILABLE if unavailable."""
    manager = get_snapshot_manager()
    current_snapshot = manager.current_snapshot
    if current_snapshot is None or manager.status == "unavailable":
        raise DataSourceError("No validated data snapshot is loaded in memory.")
    return current_snapshot


def get_filters_dependency(
    allowed_extra_params: Set[str] | None = None,
) -> Callable[[Request, Snapshot], ComplaintFilters]:
    """Factory creating a dependency that parses and validates ComplaintFilters for a specific route."""
    allowed = COMMON_FILTER_PARAMS | (allowed_extra_params or set())

    def dependency(
        request: Request,
        snapshot: Snapshot = Depends(get_current_snapshot),
    ) -> ComplaintFilters:
        query_params = request.query_params

        # 1. Enforce extra="forbid" on query parameters
        unknown_params = [k for k in query_params.keys() if k not in allowed]
        if unknown_params:
            raise ValidationException(
                message=f"Unknown query parameter(s): {unknown_params}",
                details={
                    "unknown_parameters": unknown_params,
                    "allowed_parameters": sorted(list(allowed)),
                },
            )

        # 2. Extract repeatable parameters
        try:
            filters = ComplaintFilters(
                category=query_params.getlist("category"),
                sub_category=query_params.getlist("sub_category"),
                submitted_via=query_params.getlist("submitted_via"),
                state=query_params.getlist("state"),
                company_response=query_params.getlist("company_response"),
                timely=query_params.getlist("timely"),  # type: ignore[arg-type]
                issue=query_params.getlist("issue"),
                date_from=query_params.get("date_from"),
                date_to=query_params.get("date_to"),
            )
        except Exception as exc:
            raise ValidationException(message=str(exc))

        # 3. Validate dimension values against snapshot
        filters.validate_against_snapshot(snapshot)

        return filters

    return dependency
