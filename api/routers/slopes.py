import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.state import store

router = APIRouter(prefix="/api/slopes", tags=["slopes"])


@router.get("")
def list_slopes():
    results = []
    for slope_id, slope_data in store["slopes"].items():
        risk = store["risk_results"].get(slope_id)
        entry = {
            "slope_id": slope_id,
            "name": slope_data.get("name", slope_id),
            "latitude": slope_data["latitude"],
            "longitude": slope_data["longitude"],
            "elevation_m": slope_data["elevation_m"],
            "slope_angle_deg": slope_data["slope_angle_deg"],
            "district": slope_data["district"],
            "state": slope_data["state"],
            "coverage_mode": slope_data["coverage_mode"],
            "lithology": slope_data.get("lithology", "Unknown"),
            "soil_type": slope_data.get("soil_type", "Unknown"),
            "land_cover": slope_data.get("land_cover", "Unknown"),
            "risk_score": risk["risk_score"] if risk else None,
            "priority_class": risk["priority_class"] if risk else None,
            "has_rainfall_data": slope_id in store["rainfall"] and len(store["rainfall"][slope_id]) > 0,
            "has_soil_moisture_data": slope_id in store["soil_moisture"] and len(store["soil_moisture"][slope_id]) > 0,
            "has_deformation_data": slope_id in store["deformation"] and len(store["deformation"][slope_id]) > 0,
        }
        results.append(entry)

    results.sort(key=lambda x: (x["risk_score"] or 0), reverse=True)
    return {"count": len(results), "slopes": results}


@router.get("/{slope_id}")
def get_slope_detail(slope_id: str):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")

    slope_data = store["slopes"][slope_id]
    risk = store["risk_results"].get(slope_id)
    susc = store["susceptibility_results"].get(slope_id)
    exposure = store["exposures"].get(slope_id)

    rainfall_records = store["rainfall"].get(slope_id, [])
    latest_rainfall = rainfall_records[-1].model_dump() if rainfall_records else None

    sm_records = store["soil_moisture"].get(slope_id, [])
    latest_sm = sm_records[-1].model_dump() if sm_records else None

    def_records = store["deformation"].get(slope_id, [])
    latest_def = def_records[-1].model_dump() if def_records else None

    return {
        "slope": slope_data,
        "risk": risk,
        "susceptibility": susc,
        "exposure": exposure.model_dump() if exposure else None,
        "latest_signals": {
            "rainfall": latest_rainfall,
            "soil_moisture": latest_sm,
            "deformation": latest_def,
        },
    }


@router.get("/{slope_id}/timeseries")
def get_slope_timeseries(
    slope_id: str,
    hours: Optional[int] = None,
):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")

    rainfall_records = store["rainfall"].get(slope_id, [])
    sm_records = store["soil_moisture"].get(slope_id, [])
    def_records = store["deformation"].get(slope_id, [])

    if hours is not None:
        rainfall_records = rainfall_records[-hours:] if len(rainfall_records) > hours else rainfall_records
        sm_records = sm_records[-hours:] if len(sm_records) > hours else sm_records
        def_records = def_records[-hours:] if len(def_records) > hours else def_records

    return {
        "slope_id": slope_id,
        "rainfall": [r.model_dump() for r in rainfall_records],
        "soil_moisture": [s.model_dump() for s in sm_records],
        "deformation": [d.model_dump() for d in def_records],
        "total_hours": len(rainfall_records),
    }
