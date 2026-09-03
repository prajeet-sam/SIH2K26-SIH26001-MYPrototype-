import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

from fastapi import APIRouter

from api.state import store
from data.quality.flagging import compute_data_quality_coverage, evaluate_sensor_health
from data.schemas.models import DataQualityStatus

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.get("/coverage")
def data_quality_coverage():
    all_metadata = []

    for slope_id in store["slopes"]:
        for rain_record in store["rainfall"].get(slope_id, []):
            all_metadata.append(rain_record.quality)
        for sm_record in store["soil_moisture"].get(slope_id, []):
            all_metadata.append(sm_record.quality)
        for def_record in store["deformation"].get(slope_id, []):
            all_metadata.append(def_record.quality)

    coverage = compute_data_quality_coverage(all_metadata)

    per_slope = {}
    for slope_id in store["slopes"]:
        slope_meta = []
        for rain_record in store["rainfall"].get(slope_id, []):
            slope_meta.append(rain_record.quality)
        for sm_record in store["soil_moisture"].get(slope_id, []):
            slope_meta.append(sm_record.quality)
        for def_record in store["deformation"].get(slope_id, []):
            slope_meta.append(def_record.quality)

        per_slope[slope_id] = compute_data_quality_coverage(slope_meta)

    return {
        "overall": coverage,
        "per_slope": per_slope,
        "provenance": "Simulated (Demo)",
        "computed_at": datetime.utcnow().isoformat(),
    }


@router.get("/sensors")
def sensor_health_status():
    sensor_summary = {
        "total_sensors": 0,
        "healthy": 0,
        "stale": 0,
        "missing": 0,
        "inconsistent": 0,
    }

    slope_details = {}

    for slope_id in store["slopes"]:
        sensors = {"rainfall": None, "soil_moisture": None, "deformation": None}

        rain_records = store["rainfall"].get(slope_id, [])
        if rain_records:
            last_ts = rain_records[-1].timestamp
            health = evaluate_sensor_health(last_ts)
            sensors["rainfall"] = {
                "status": health.value,
                "last_reading": last_ts.isoformat(),
                "record_count": len(rain_records),
            }
            sensor_summary["total_sensors"] += 1
            sensor_summary[health.value.lower()] = sensor_summary.get(health.value.lower(), 0) + 1

        sm_records = store["soil_moisture"].get(slope_id, [])
        if sm_records:
            last_ts = sm_records[-1].timestamp
            health = evaluate_sensor_health(last_ts)
            sensors["soil_moisture"] = {
                "status": health.value,
                "last_reading": last_ts.isoformat(),
                "record_count": len(sm_records),
            }
            sensor_summary["total_sensors"] += 1
            sensor_summary[health.value.lower()] = sensor_summary.get(health.value.lower(), 0) + 1

        def_records = store["deformation"].get(slope_id, [])
        if def_records:
            last_ts = def_records[-1].timestamp
            health = evaluate_sensor_health(last_ts)
            sensors["deformation"] = {
                "status": health.value,
                "last_reading": last_ts.isoformat(),
                "record_count": len(def_records),
            }
            sensor_summary["total_sensors"] += 1
            sensor_summary[health.value.lower()] = sensor_summary.get(health.value.lower(), 0) + 1

        slope_details[slope_id] = {
            "coverage_mode": store["slopes"][slope_id]["coverage_mode"],
            "sensors": sensors,
        }

    return {
        "summary": sensor_summary,
        "per_slope": slope_details,
        "checked_at": datetime.utcnow().isoformat(),
    }
