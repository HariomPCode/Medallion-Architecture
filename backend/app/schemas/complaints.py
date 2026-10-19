"""
backend/app/schemas/complaints.py
---------------------------------
Pydantic schemas for Complaint Explorer endpoints (§13.3).
Exposes only whitelisted public fields, avoiding internal leaks.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComplaintListItem(BaseModel):
    """Projection of public complaint fields for explorer table rows."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: int = Field(..., description="Unique CFPB complaint ID")
    date_submitted: str = Field(..., description="ISO 8601 date when complaint was submitted")
    category: str = Field(..., description="High-level financial product category")
    sub_category: str = Field(..., description="Sub-category within the product domain")
    product: str = Field(..., description="Specific financial product")
    issue: str = Field(..., description="Primary issue reported by consumer")
    submitted_via: str = Field(..., description="Submission channel (Web, Referral, Phone, etc.)")
    state: str | None = Field(None, description="Consumer US state or territory abbreviation")
    company_response: str = Field(..., description="Company response classification")
    timely_response: Literal["yes", "no"] | None = Field(
        None,
        description="Whether company response was timely ('yes', 'no', or null for in-progress)",
    )
    is_anomaly: bool | None = Field(
        None,
        description="Whether complaint was flagged as anomalous by Isolation Forest model",
    )


class ComplaintListResponse(BaseModel):
    """Paginated complaint list response envelope."""

    model_config = ConfigDict(extra="forbid")

    items: list[ComplaintListItem] = Field(
        ..., description="List of complaint records for the page"
    )
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page (max 100)")
    total: int = Field(..., ge=0, description="Total matching complaints across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages available")


class ComplaintDetailResponse(BaseModel):
    """Full detail response for a single complaint record."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: int = Field(..., description="Unique CFPB complaint ID")
    date_submitted: str = Field(..., description="ISO 8601 date when complaint was submitted")
    date_received: str | None = Field(
        None, description="ISO 8601 date when CFPB routed complaint to company"
    )
    days_submitted_to_received: int | None = Field(
        None,
        description="CFPB routing delay in days (Date_received - Date_submitted). Not company response time.",
    )
    category: str = Field(..., description="High-level financial product category")
    sub_category: str = Field(..., description="Sub-category within the product domain")
    product: str = Field(..., description="Specific financial product")
    sub_product: str | None = Field(None, description="Detailed sub-product classification")
    issue: str = Field(..., description="Primary issue reported by consumer")
    sub_issue: str | None = Field(None, description="Detailed sub-issue description")
    submitted_via: str = Field(..., description="Submission channel")
    state: str | None = Field(None, description="Consumer US state or territory")
    company_response: str = Field(..., description="Company response classification")
    company_public_response: str | None = Field(
        None, description="Public response text from company (if provided)"
    )
    timely_response: Literal["yes", "no"] | None = Field(
        None, description="Whether response was timely ('yes', 'no', or null)"
    )
    is_anomaly: bool | None = Field(None, description="Whether flagged as anomaly")
    anomaly_score: float | None = Field(
        None,
        description="Isolation Forest decision function score (lower values = more unusual)",
    )
