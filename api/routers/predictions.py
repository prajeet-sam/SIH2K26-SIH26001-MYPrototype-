import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException

from api.state import store, susceptibility_predictor, dynamic_predictor, risk_engine, audit_logger
import api.state as state
from ml.susceptibility.features import (
    prepare_feature_matrix_from_dataframe,
    encode_lithology,
    encode_soil_type,
    encode_land_cover,
)
from ml.dynamic.features import build_dynamic_feature_matrix

import pandas as pd

router = APIRouter(prefix="/api/predict", tags=["predictions"])


def _get_slope_features(slope_id: str) -> pd.DataFrame:
    slope_data = store["slopes"][slope_id]
    rainfall_records = store["rainfall"].get(slope_id, [])
    sm_records = store["soil_moisture"].get(slope_id, [])
    def_records = store["deformation"].get(slope_id, [])

    rain_vals = [r.rainfall_mm for r in rainfall_records[-72:]] if rainfall_records else [0.0]
    sm_vals = [s.volumetric_water_content for s in sm_records[-72:]] if sm_records else [0.25]
    def_vals = [d.displacement_mm for d in def_records[-72:]] if def_records else [0.5]

    row = {
        "slope_angle": slope_data["slope_angle_deg"],
        "elevation": slope_data["elevation_m"],
        "aspect": slope_data["aspect_deg"],
        "curvature": slope_data["curvature"],
        "drainage_density": slope_data.get("drainage_density", 1.5),
        "lithology_encoded": encode_lithology(slope_data.get("lithology", "mixed")),
        "soil_type_encoded": encode_soil_type(slope_data.get("soil_type", "residual")),
        "land_cover_encoded": encode_land_cover(slope_data.get("land_cover", "bare_soil")),
        "rain_cum": sum(rain_vals),
        "rain_max": max(rain_vals),
        "rain_mean": float(np.mean(rain_vals)),
        "rain_std": float(np.std(rain_vals)),
        "rain_intensity": sum(rain_vals) / max(1, len(rain_vals)),
        "sm_current": sm_vals[-1] if sm_vals else 0.25,
        "sm_mean": float(np.mean(sm_vals)),
        "sm_trend": (sm_vals[-1] - sm_vals[0]) if len(sm_vals) > 1 else 0.0,
        "def_current": def_vals[-1] if def_vals else 0.5,
        "def_max": max(def_vals),
        "def_trend": (def_vals[-1] - def_vals[0]) if len(def_vals) > 1 else 0.0,
        "def_accel": (def_vals[-1] - 2 * def_vals[len(def_vals)//2] + def_vals[0]) if len(def_vals) > 2 else 0.0,
    }
    df = pd.DataFrame([row])
    return df


def _get_dynamic_features(slope_id: str) -> pd.DataFrame:
    slope_data = store["slopes"][slope_id]
    rainfall_records = store["rainfall"].get(slope_id, [])
    sm_records = store["soil_moisture"].get(slope_id, [])
    def_records = store["deformation"].get(slope_id, [])

    rain_df = pd.DataFrame([r.model_dump() for r in rainfall_records]) if rainfall_records else pd.DataFrame({"timestamp": [], "rainfall_mm": []})
    sm_df = pd.DataFrame([s.model_dump() for s in sm_records]) if sm_records else pd.DataFrame({"timestamp": [], "volumetric_water_content": []})
    def_df = pd.DataFrame([d.model_dump() for d in def_records]) if def_records else pd.DataFrame({"timestamp": [], "displacement_mm": []})

    merged = rain_df[["timestamp", "rainfall_mm"]].copy() if not rain_df.empty else pd.DataFrame({"timestamp": [], "rainfall_mm": []})

    if not sm_df.empty and "volumetric_water_content" in sm_df.columns:
        merged = merged.merge(sm_df[["timestamp", "volumetric_water_content"]], on="timestamp", how="left")
    else:
        merged["volumetric_water_content"] = 0.25

    if not def_df.empty and "displacement_mm" in def_df.columns:
        merged = merged.merge(def_df[["timestamp", "displacement_mm"]], on="timestamp", how="left")
    else:
        merged["displacement_mm"] = 0.5

    merged["susceptibility_probability"] = 0.5
    merged["slope_angle"] = slope_data["slope_angle_deg"]
    merged["elevation_m"] = slope_data["elevation_m"]
    merged["aspect_deg"] = slope_data["aspect_deg"]
    merged["curvature"] = slope_data["curvature"]

    last_row = merged.iloc[[-1]].copy()
    last_row["slope_id"] = slope_id

    return build_dynamic_feature_matrix(last_row)


@router.post("/susceptibility/{slope_id}")
def predict_susceptibility(slope_id: str):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")
    if state.susceptibility_predictor is None:
        raise HTTPException(status_code=503, detail="Susceptibility model not trained yet")

    try:
        X = _get_slope_features(slope_id)
        results = state.susceptibility_predictor.predict_with_shap(X, slope_ids=[slope_id])
        result = results[0] if results else {}

        output = {
            "slope_id": slope_id,
            "susceptibility_probability": result.get("susceptibility_probability", 0.0),
            "confidence": abs(result.get("susceptibility_probability", 0.5) - 0.5) * 2,
            "model_version": result.get("model_version", "unknown"),
            "feature_contributions": result.get("feature_contributions", {}),
            "computed_at": datetime.utcnow().isoformat(),
        }
        store["susceptibility_results"][slope_id] = output

        audit_logger.log_prediction(slope_id, {
            "type": "susceptibility",
            "probability": output["susceptibility_probability"],
            "confidence": output["confidence"],
        })

        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hazard/{slope_id}")
def predict_hazard(slope_id: str, horizon: int = 24):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")
    if state.dynamic_predictor is None:
        raise HTTPException(status_code=503, detail="Dynamic hazard model not trained yet")
    if horizon not in state.dynamic_predictor.models:
        raise HTTPException(status_code=400, detail=f"Horizon {horizon}h not available")

    try:
        X = _get_dynamic_features(slope_id)
        results = state.dynamic_predictor.predict_with_shap(X, horizon=horizon)
        result = results[0] if results else {}

        output = {
            "slope_id": slope_id,
            "hazard_probability": result.get("hazard_probability", 0.0),
            "confidence": abs(result.get("hazard_probability", 0.5) - 0.5) * 2,
            "forecast_horizon_hours": horizon,
            "model_version": result.get("model_version", "unknown"),
            "feature_contributions": result.get("feature_contributions", {}),
            "computed_at": datetime.utcnow().isoformat(),
        }
        store["hazard_results"][slope_id] = output

        audit_logger.log_prediction(slope_id, {
            "type": "hazard",
            "horizon": horizon,
            "probability": output["hazard_probability"],
            "confidence": output["confidence"],
        })

        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/{slope_id}")
def compute_risk(slope_id: str, horizon: int = 24):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")

    susc_result = store["susceptibility_results"].get(slope_id)
    hazard_result = store["hazard_results"].get(slope_id)

    if hazard_result is None:
        try:
            predict_hazard(slope_id, horizon=horizon)
            hazard_result = store["hazard_results"].get(slope_id)
        except Exception:
            pass

    if hazard_result is None:
        hazard_prob = susc_result["susceptibility_probability"] if susc_result else 0.5
        confidence = susc_result["confidence"] if susc_result else 0.3
    else:
        hazard_prob = hazard_result["hazard_probability"]
        confidence = hazard_result["confidence"]

    exposure = store["exposures"].get(slope_id)
    risk_output = risk_engine.compute_risk(slope_id, hazard_prob, exposure, confidence)

    store["risk_results"][slope_id] = risk_output.model_dump()

    audit_logger.log_prediction(slope_id, {
        "type": "risk",
        "risk_score": risk_output.risk_score,
        "priority_class": risk_output.priority_class,
        "hazard_component": risk_output.hazard_component,
        "exposure_component": risk_output.exposure_component,
        "confidence": risk_output.confidence,
    })

    return risk_output.model_dump()


@router.get("/all")
def predict_all():
    results = []
    for slope_id in store["slopes"]:
        try:
            susc_result = store["susceptibility_results"].get(slope_id)
            if susc_result is None:
                predict_susceptibility(slope_id)

            hazard_result = store["hazard_results"].get(slope_id)
            if hazard_result is None:
                predict_hazard(slope_id, horizon=24)

            risk_result = store["risk_results"].get(slope_id)
            if risk_result is None:
                compute_risk(slope_id)

            results.append({
                "slope_id": slope_id,
                "susceptibility": store["susceptibility_results"].get(slope_id),
                "hazard": store["hazard_results"].get(slope_id),
                "risk": store["risk_results"].get(slope_id),
            })
        except Exception as e:
            results.append({
                "slope_id": slope_id,
                "error": str(e),
            })

    results.sort(key=lambda x: (x.get("risk", {}) or {}).get("risk_score", 0) if x.get("risk") else 0, reverse=True)
    return {"count": len(results), "predictions": results}
