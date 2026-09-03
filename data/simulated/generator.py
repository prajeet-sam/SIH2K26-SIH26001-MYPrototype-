import random
import math
from datetime import datetime, timedelta
from typing import Optional
from data.schemas.models import (
    DataQualityMetadata,
    DataQualityStatus,
    ProvenanceTag,
    RainfallRecord,
    SoilMoistureRecord,
    DeformationRecord,
    CoverageMode,
)


def _quality_meta(source: str = "simulated_sensor") -> DataQualityMetadata:
    return DataQualityMetadata(
        timestamp=datetime.utcnow(),
        source=source,
        spatial_accuracy_m=10.0,
        sensor_health=DataQualityStatus.HEALTHY,
        provenance=ProvenanceTag.SIMULATED_DEMO,
    )


def generate_soil_moisture_series(
    slope_id: str,
    start: datetime,
    hours: int = 168,
    rainfall_records: Optional[list] = None,
) -> list[SoilMoistureRecord]:
    """Generate soil moisture that responds to actual rainfall infiltration."""
    rng = random.Random(hash(slope_id) % (2**31) + 1)
    records = []
    base_vwc = 0.18 + rng.random() * 0.12
    vwc = base_vwc
    antecedent_rain = 0.0

    rain_map = {}
    if rainfall_records:
        for r in rainfall_records:
            rain_map[r.timestamp.hour + (r.timestamp - start).days * 24] = r.rainfall_mm

    for h in range(hours):
        ts = start + timedelta(hours=h)

        rain_mm = rain_map.get(h, 0.0)
        antecedent_rain = antecedent_rain * 0.85 + rain_mm

        infiltration = antecedent_rain * 0.003
        drainage = (vwc - base_vwc) * 0.08
        evapotranspiration = 0.001 if 6 <= ts.hour <= 18 else 0.0

        vwc += infiltration - drainage - evapotranspiration + rng.gauss(0, 0.001)
        vwc = max(0.05, min(0.55, vwc))

        rate = vwc - base_vwc
        sensor_health = DataQualityStatus.HEALTHY
        if rng.random() < 0.02:
            sensor_health = DataQualityStatus.STALE

        records.append(SoilMoistureRecord(
            slope_id=slope_id,
            timestamp=ts,
            volumetric_water_content=round(vwc, 4),
            depth_cm=50,
            rate_of_change=round(rate, 5),
            quality=DataQualityMetadata(
                timestamp=datetime.utcnow(),
                source="simulated_soil_sensor",
                spatial_accuracy_m=5.0,
                sensor_health=sensor_health,
                provenance=ProvenanceTag.SIMULATED_DEMO,
            ),
        ))

    return records


def generate_deformation_series(
    slope_id: str,
    start: datetime,
    hours: int = 168,
    slope_angle_deg: float = 35.0,
    rainfall_records: Optional[list] = None,
    soil_moisture_records: Optional[list] = None,
) -> list[DeformationRecord]:
    """Generate displacement correlated with rainfall and soil moisture."""
    rng = random.Random(hash(slope_id) % (2**31) + 2)
    records = []
    cumulative = 0.0
    slope_factor = slope_angle_deg / 55.0

    rain_cumulative = 0.0
    vwc_current = 0.20
    rain_map = {}
    sm_map = {}

    if rainfall_records:
        for r in rainfall_records:
            rain_map[r.timestamp] = r.rainfall_mm
    if soil_moisture_records:
        for s in soil_moisture_records:
            sm_map[s.timestamp] = s.volumetric_water_content

    for h in range(hours):
        ts = start + timedelta(hours=h)

        rain_mm = rain_map.get(ts, 0.0)
        rain_cumulative = rain_cumulative * 0.9 + rain_mm

        vwc_current = sm_map.get(ts, vwc_current)
        moisture_factor = max(0, (vwc_current - 0.20) / 0.35)

        base_rate = 0.05 * slope_factor
        rain_effect = rain_cumulative * 0.02 * slope_factor
        moisture_effect = moisture_factor * 0.3 * slope_factor
        noise = abs(rng.gauss(0, 0.02))

        rate = base_rate + rain_effect + moisture_effect + noise
        cumulative += rate

        sensor_health = DataQualityStatus.HEALTHY
        if rng.random() < 0.02:
            sensor_health = DataQualityStatus.STALE

        records.append(DeformationRecord(
            slope_id=slope_id,
            timestamp=ts,
            displacement_mm=round(rate, 3),
            displacement_rate_mm_day=round(rate * 24, 3),
            cumulative_displacement_mm=round(cumulative, 3),
            source="simulated_tiltmeter",
            quality=DataQualityMetadata(
                timestamp=datetime.utcnow(),
                source="simulated_tiltmeter",
                spatial_accuracy_m=1.0,
                sensor_health=sensor_health,
                provenance=ProvenanceTag.SIMULATED_DEMO,
            ),
        ))

    return records
