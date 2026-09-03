from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProvenanceTag(str, Enum):
    OBSERVED = "Observed"
    FORECAST = "Forecast"
    ESTIMATED = "Estimated"
    INTERPOLATED = "Interpolated"
    MODEL_DERIVED = "Model-derived"
    SIMULATED_DEMO = "Simulated (Demo)"


class CoverageMode(str, Enum):
    INSTRUMENTED = "Instrumented"
    MODELED_ONLY = "Modeled-only"


class DataQualityStatus(str, Enum):
    HEALTHY = "Healthy"
    STALE = "Stale"
    MISSING = "Missing"
    INCONSISTENT = "Inconsistent"
    LOW_CONFIDENCE = "Low Confidence"


class DataQualityMetadata(BaseModel):
    timestamp: datetime
    source: str
    spatial_accuracy_m: Optional[float] = None
    sensor_health: DataQualityStatus = DataQualityStatus.HEALTHY
    missing_data_status: Optional[str] = None
    provenance: ProvenanceTag = ProvenanceTag.OBSERVED


class SlopeUnit(BaseModel):
    slope_id: str
    latitude: float
    longitude: float
    elevation_m: float
    slope_angle_deg: float
    aspect_deg: float
    curvature: float
    area_sq_km: float
    district: str
    state: str
    coverage_mode: CoverageMode = CoverageMode.MODELED_ONLY
    quality: DataQualityMetadata


class RainfallRecord(BaseModel):
    slope_id: str
    timestamp: datetime
    rainfall_mm: float
    intensity_mm_hr: Optional[float] = None
    cumulative_24h_mm: Optional[float] = None
    cumulative_72h_mm: Optional[float] = None
    is_forecast: bool = False
    forecast_horizon_hours: Optional[int] = None
    quality: DataQualityMetadata


class SoilMoistureRecord(BaseModel):
    slope_id: str
    timestamp: datetime
    volumetric_water_content: float
    depth_cm: float
    rate_of_change: Optional[float] = None
    quality: DataQualityMetadata


class DeformationRecord(BaseModel):
    slope_id: str
    timestamp: datetime
    displacement_mm: float
    displacement_rate_mm_day: Optional[float] = None
    cumulative_displacement_mm: Optional[float] = None
    source: str  # e.g., "InSAR", "GNSS", "tiltmeter"
    quality: DataQualityMetadata


class GeologicalRecord(BaseModel):
    slope_id: str
    lithology: str
    soil_type: str
    rock_strength: Optional[str] = None
    permeability: Optional[str] = None
    geotechnical_quality: DataQualityStatus = DataQualityStatus.HEALTHY
    quality: DataQualityMetadata


class LandCoverRecord(BaseModel):
    slope_id: str
    timestamp: datetime
    land_cover_class: str
    vegetation_index: Optional[float] = None  # NDVI
    change_detected: bool = False
    previous_class: Optional[str] = None
    quality: DataQualityMetadata


class ExposureRecord(BaseModel):
    slope_id: str
    nearest_road_distance_m: Optional[float] = None
    road_criticality: Optional[str] = None  # "National", "State", "District"
    nearest_bridge_distance_m: Optional[float] = None
    nearest_settlement_distance_m: Optional[float] = None
    estimated_population: Optional[int] = None
    has_school: bool = False
    has_hospital: bool = False
    has_critical_infrastructure: bool = False
    quality: DataQualityMetadata


class HistoricalEvent(BaseModel):
    event_id: str
    slope_id: Optional[str] = None
    latitude: float
    longitude: float
    date: datetime
    event_type: str  # "slide", "debris_flow", "rockfall"
    area_sq_km: Optional[float] = None
    trigger: Optional[str] = None  # "rainfall", "earthquake", "unknown"
    confidence: float = Field(ge=0, le=1)
    source: str
    quality: DataQualityMetadata


class SusceptibilityOutput(BaseModel):
    slope_id: str
    susceptibility_probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    model_version: str
    feature_contributions: Optional[dict] = None
    provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED
    computed_at: datetime


class HazardOutput(BaseModel):
    slope_id: str
    hazard_probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    forecast_horizon_hours: int
    model_version: str
    feature_contributions: Optional[dict] = None
    provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED
    computed_at: datetime


class RiskOutput(BaseModel):
    slope_id: str
    risk_score: int = Field(ge=0, le=100)
    priority_class: str  # "Low", "Moderate", "High", "Critical"
    hazard_component: float = Field(ge=0, le=1)
    exposure_component: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    uncertainty_notes: Optional[str] = None
    provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED
    computed_at: datetime


class AlertLevel(str, Enum):
    WATCH = "Watch"
    WARNING = "Warning"
    CRITICAL = "Critical"


class CandidateAlert(BaseModel):
    alert_id: str
    slope_id: str
    level: AlertLevel
    hazard_probability: float
    risk_score: int
    confidence: float
    contributing_evidence: list[str]
    recommended_action: str
    generated_at: datetime
    provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class AuditRecord(BaseModel):
    record_id: str
    record_type: str  # "prediction", "alert", "feedback"
    slope_id: str
    timestamp: datetime
    data: dict
    provenance: ProvenanceTag
