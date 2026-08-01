from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class ProcessingSettingsSchema(BaseModel):
    model_name: str = "voyager205/sdg-variant-finetuned"
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    use_hybrid: bool = True
    ensemble_mode: str = "weighted"
    min_words: int = Field(default=20, ge=5, le=200)
    max_words: int = Field(default=500, ge=50, le=2000)
    top_activities: int = Field(default=0, ge=0)
    enable_bias_corrections: bool = True
    bias_corrections: dict[int, bool] = {}
    use_custom_thresholds: bool = False
    sdg_thresholds: dict[int, float] = {}
    require_action_verb: bool = False


class AnalysisJobResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    progress: float
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    # Set by the upload route when a completed analysis for the same council-year
    # already exists (skip-if-exists); no new analysis is created. Always
    # false/None on the job and results routes.
    skipped: bool = False
    existing_id: Optional[str] = None

    model_config = {"from_attributes": True}


class AnalysisSummary(BaseModel):
    source: str
    total_activities: int
    mean_alignment_score: float
    mean_scores: dict[int, float]
    top_sdgs: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    coverage: dict[int, float] | None = None
    # Extraction quality (data-contract Part C #5)
    page_count: int | None = None
    activities_per_100_pages: float | None = None
    barren_activities: int | None = None


class AnalysisResultResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    summary: Optional[AnalysisSummary] = None
    activities: Optional[list[dict[str, Any]]] = None
    settings: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ActivityPageResponse(BaseModel):
    activities: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    sdg_filter: Optional[int] = None


class CompareRequest(BaseModel):
    analysis_ids: list[str]


class AnalysisListItem(BaseModel):
    id: str
    original_filename: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
