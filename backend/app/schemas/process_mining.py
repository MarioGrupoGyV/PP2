from uuid import UUID

from pydantic import BaseModel


class ActivityBoundary(BaseModel):
    activity: str
    frequency: int
    percentage: float


class ActivityStatistic(BaseModel):
    activity: str
    frequency: int
    case_frequency: int


class DfgNode(ActivityStatistic):
    pass


class DfgEdge(BaseModel):
    source: str
    target: str
    frequency: int
    case_frequency: int
    percentage: float


class DfgResponse(BaseModel):
    nodes: list[DfgNode]
    edges: list[DfgEdge]
    start_activities: list[ActivityBoundary]
    end_activities: list[ActivityBoundary]


class TransitionStatistic(DfgEdge):
    average_duration_seconds: float
    median_duration_seconds: float
    min_duration_seconds: float
    max_duration_seconds: float


class PerformanceResponse(BaseModel):
    transitions: list[TransitionStatistic]


class VariantStatistic(BaseModel):
    variant_id: str
    activities: list[str]
    case_count: int
    percentage: float


class VariantCase(BaseModel):
    id: UUID
    case_code: str


class VariantCasesResponse(BaseModel):
    variant_id: str
    case_count: int
    page: int
    page_size: int
    total_pages: int
    cases: list[VariantCase]


class ProcessMiningSummary(BaseModel):
    total_cases: int
    total_events: int
    unique_activities: int
    total_variants: int
    average_case_duration_seconds: float
    median_case_duration_seconds: float
