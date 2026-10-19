"""
backend/app/schemas/quality.py
------------------------------
Pydantic schemas for Data Quality Center and Anomaly endpoints (§13.3).
Exposes decomposed quality dimensions, anomaly distributions, model metadata, and annotations.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QualityDimension(BaseModel):
    """Individual decomposed quality dimension."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Machine-readable dimension identifier")
    label: str = Field(..., description="Human-readable dimension label")
    value: float = Field(..., description="Dimension score percentage (0-100)")
    weight: float = Field(..., description="Weight in composite overall score formula")
    definition: str = Field(..., description="Formula definition and criteria from pipeline logic")
    note: str = Field(..., description="Contextual note explaining deductions or data drivers")


class CategoryAnomalyItem(BaseModel):
    """Anomaly counts and rate for a category."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., description="Financial product category")
    flagged: int = Field(..., ge=0, description="Number of flagged anomaly records")
    total: int = Field(..., ge=0, description="Total records in this category")
    rate_pct: float = Field(..., ge=0.0, description="Flagged percentage within category")


class CompanyResponseAnomalyItem(BaseModel):
    """Anomaly counts and rate for a company response classification."""

    model_config = ConfigDict(extra="forbid")

    company_response: str = Field(..., description="Company response status")
    flagged: int = Field(..., ge=0, description="Number of flagged anomaly records")
    total: int = Field(..., ge=0, description="Total records with this response")
    rate_pct: float = Field(..., ge=0.0, description="Flagged percentage within response type")


class AnomalySummaryBlock(BaseModel):
    """Aggregate anomaly metrics from Isolation Forest model run."""

    model_config = ConfigDict(extra="forbid")

    flagged: int = Field(..., ge=0, description="Total complaints flagged as anomalous")
    rate_pct: float = Field(..., ge=0.0, description="Flagged rate over total dataset")
    in_progress_share_pct: float | None = Field(
        None,
        description="Percentage of flagged anomalies that represent open/in-progress cases",
    )
    by_category: list[CategoryAnomalyItem] = Field(
        default_factory=list, description="Distribution of anomalies across categories"
    )
    by_company_response: list[CompanyResponseAnomalyItem] = Field(
        default_factory=list, description="Distribution of anomalies across company responses"
    )


class ModelMetadata(BaseModel):
    """Isolation Forest anomaly detection model parameters and provenance."""

    model_config = ConfigDict(extra="forbid")

    available: bool = Field(..., description="Whether model run metadata was published by pipeline")
    type: str = Field("IsolationForest", description="Algorithm name")
    contamination: float = Field(..., description="Expected proportion of outliers in the data")
    n_estimators: int = Field(..., description="Number of isolation trees in the ensemble")
    features: list[str] = Field(
        default_factory=list, description="Feature columns used during training"
    )
    mlflow_run_id: str | None = Field(None, description="MLflow tracking run ID")
    source: Literal["run_metadata", "notebook_constant"] = Field(
        ...,
        description="Source of model parameters (published run metadata vs documented notebook constants)",
    )


class QualityTimestamps(BaseModel):
    """Timestamps reflecting quality analysis execution and report freshness."""

    model_config = ConfigDict(extra="forbid")

    quality_analysis_at: str | None = Field(
        None, description="ISO 8601 UTC timestamp when DQ pipeline model was executed"
    )
    report_object_refreshed_at: str = Field(
        ..., description="ISO 8601 UTC timestamp when DQ report object was refreshed in storage"
    )


class QualitySummaryResponse(BaseModel):
    """Complete Data Quality Center summary card payload."""

    model_config = ConfigDict(extra="forbid")

    overall_quality_score: float = Field(
        ..., description="Weighted composite data quality score (0-100)"
    )
    status: Literal["HIGH QUALITY", "MODERATE QUALITY", "LOW QUALITY"] = Field(
        ..., description="Quality band derived from composite score"
    )
    total_records: int = Field(..., ge=0, description="Total records evaluated in DQ report")
    dimensions: list[QualityDimension] = Field(
        ..., description="Decomposed quality dimensions (Completeness, Validity, etc.)"
    )
    anomalies: AnomalySummaryBlock = Field(
        ..., description="Summary of Isolation Forest anomaly detections"
    )
    model: ModelMetadata = Field(..., description="Anomaly model parameters and run metadata")
    timestamps: QualityTimestamps = Field(..., description="Provenance timestamps")
    limitations: list[str] = Field(
        ..., description="Mandatory limitations and methodological caveats (§6 A-05..A-08)"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Integrity warnings or discrepancies detected at runtime"
    )


class AnomalyAnnotations(BaseModel):
    """Deterministic observations attached to individual anomaly records."""

    model_config = ConfigDict(extra="forbid")

    open_case: bool = Field(
        ..., description="Observation: complaint is open/in-progress with no final resolution"
    )
    long_routing_delay: bool = Field(
        ..., description="Observation: CFPB intake/routing lag was >= 7 days"
    )
    timely_no: bool = Field(..., description="Observation: company response was marked untimely")


class AnomalyListItem(BaseModel):
    """Single anomaly record with join fields and deterministic annotations."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: int = Field(..., description="CFPB complaint ID")
    date_submitted: str = Field(..., description="ISO date complaint was submitted")
    category: str = Field(..., description="High-level financial product category")
    sub_category: str = Field(..., description="Sub-category")
    product: str = Field(..., description="Specific product")
    issue: str = Field(..., description="Complaint issue")
    submitted_via: str = Field(..., description="Submission channel")
    state: str | None = Field(None, description="Consumer state")
    company_response: str = Field(..., description="Company response classification")
    timely_response: Literal["yes", "no"] | None = Field(
        None, description="Timely response status ('yes', 'no', or null)"
    )
    days_submitted_to_received: int | None = Field(
        None, description="CFPB intake routing delay in days"
    )
    anomaly_score: float = Field(
        ..., description="Decision function score from Isolation Forest (lower = more unusual)"
    )
    is_anomaly: bool = Field(..., description="Whether flagged as anomaly by model")
    annotations: AnomalyAnnotations = Field(
        ..., description="Deterministic observational flags (not model explanations)"
    )
    annotations_note: str = Field(
        "Observations, not model explanations",
        description="Clarifying note distinguishing factual observations from ML feature importances",
    )


class AnomalyListResponse(BaseModel):
    """Paginated anomaly list response wrapper."""

    model_config = ConfigDict(extra="forbid")

    items: list[AnomalyListItem] = Field(..., description="Anomaly records for current page")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page (max 100)")
    total: int = Field(..., ge=0, description="Total matching anomaly records")
    total_pages: int = Field(..., ge=0, description="Total pages available")
