from datetime import datetime, timedelta
from typing import Optional
from data.schemas.models import (
    DataQualityMetadata,
    DataQualityStatus,
    ProvenanceTag,
)


STALE_THRESHOLD_HOURS = 6
MISSING_THRESHOLD_HOURS = 24


def evaluate_sensor_health(
    last_reading_time: datetime,
    current_time: Optional[datetime] = None,
) -> DataQualityStatus:
    if current_time is None:
        current_time = datetime.utcnow()
    elapsed = current_time - last_reading_time
    if elapsed > timedelta(hours=MISSING_THRESHOLD_HOURS):
        return DataQualityStatus.MISSING
    if elapsed > timedelta(hours=STALE_THRESHOLD_HOURS):
        return DataQualityStatus.STALE
    return DataQualityStatus.HEALTHY


def validate_range(
    value: float,
    min_val: float,
    max_val: float,
    field_name: str = "value",
) -> Optional[str]:
    if value < min_val or value > max_val:
        return f"{field_name}={value} outside plausible range [{min_val}, {max_val}]"
    return None


def create_quality_metadata(
    source: str,
    provenance: ProvenanceTag = ProvenanceTag.OBSERVED,
    sensor_health: DataQualityStatus = DataQualityStatus.HEALTHY,
    spatial_accuracy_m: Optional[float] = None,
    missing_data_status: Optional[str] = None,
) -> DataQualityMetadata:
    return DataQualityMetadata(
        timestamp=datetime.utcnow(),
        source=source,
        spatial_accuracy_m=spatial_accuracy_m,
        sensor_health=sensor_health,
        missing_data_status=missing_data_status,
        provenance=provenance,
    )


def flag_record_quality(
    metadata: DataQualityMetadata,
    value_range_valid: bool = True,
    sensor_stale: bool = False,
) -> DataQualityMetadata:
    if sensor_stale:
        metadata.sensor_health = DataQualityStatus.STALE
    if not value_range_valid:
        metadata.sensor_health = DataQualityStatus.INCONSISTENT
    return metadata


def compute_data_quality_coverage(
    records: list[DataQualityMetadata],
) -> dict:
    total = len(records)
    if total == 0:
        return {"total": 0, "healthy_pct": 0, "stale_pct": 0, "missing_pct": 0, "inconsistent_pct": 0}
    healthy = sum(1 for r in records if r.sensor_health == DataQualityStatus.HEALTHY)
    stale = sum(1 for r in records if r.sensor_health == DataQualityStatus.STALE)
    missing = sum(1 for r in records if r.sensor_health == DataQualityStatus.MISSING)
    inconsistent = sum(1 for r in records if r.sensor_health == DataQualityStatus.INCONSISTENT)
    return {
        "total": total,
        "healthy_pct": round(healthy / total * 100, 1),
        "stale_pct": round(stale / total * 100, 1),
        "missing_pct": round(missing / total * 100, 1),
        "inconsistent_pct": round(inconsistent / total * 100, 1),
    }
