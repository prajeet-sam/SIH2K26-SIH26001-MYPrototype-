import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

from fastapi import APIRouter, HTTPException

from api.state import store, alert_generator, audit_logger
from data.schemas.models import RiskOutput, ProvenanceTag

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _extract_recent_signals(slope_id: str) -> dict:
    rainfall_records = store["rainfall"].get(slope_id, [])
    sm_records = store["soil_moisture"].get(slope_id, [])
    def_records = store["deformation"].get(slope_id, [])

    rainfall_elevated = False
    if len(rainfall_records) >= 6:
        recent_cum = sum(r.rainfall_mm for r in rainfall_records[-6:])
        rainfall_elevated = recent_cum > 30

    soil_moisture_rising = False
    if len(sm_records) >= 6:
        recent_vwc = [s.volumetric_water_content for s in sm_records[-6:]]
        if len(recent_vwc) >= 2:
            soil_moisture_rising = recent_vwc[-1] > recent_vwc[0] * 1.1

    deformation_detected = False
    if len(def_records) >= 3:
        recent_rates = [d.displacement_rate_mm_day or 0 for d in def_records[-3:]]
        deformation_detected = any(r > 2.0 for r in recent_rates)

    return {
        "rainfall_elevated": rainfall_elevated,
        "soil_moisture_rising": soil_moisture_rising,
        "deformation_detected": deformation_detected,
    }


@router.get("")
def list_alerts():
    alerts = list(store["alerts"].values())
    alerts.sort(key=lambda a: a.get("generated_at", ""), reverse=True)
    return {"count": len(alerts), "alerts": alerts}


@router.post("/evaluate/{slope_id}")
def evaluate_alert(slope_id: str):
    if slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {slope_id} not found")

    risk_data = store["risk_results"].get(slope_id)
    if risk_data is None:
        try:
            from api.routers.predictions import compute_risk
            compute_risk(slope_id)
            risk_data = store["risk_results"].get(slope_id)
        except Exception:
            risk_data = {
                "slope_id": slope_id,
                "risk_score": 50,
                "priority_class": "Moderate",
                "hazard_component": 0.5,
                "exposure_component": 0.5,
                "confidence": 0.3,
            }

    risk_output = RiskOutput(
        slope_id=risk_data["slope_id"],
        risk_score=risk_data["risk_score"],
        priority_class=risk_data["priority_class"],
        hazard_component=risk_data["hazard_component"],
        exposure_component=risk_data["exposure_component"],
        confidence=risk_data["confidence"],
        uncertainty_notes=risk_data.get("uncertainty_notes"),
        provenance=ProvenanceTag.MODEL_DERIVED,
        computed_at=datetime.fromisoformat(risk_data["computed_at"]) if isinstance(risk_data.get("computed_at"), str) else datetime.utcnow(),
    )

    recent_signals = _extract_recent_signals(slope_id)

    alert = alert_generator.evaluate(slope_id, risk_output, recent_signals)
    if alert is None:
        return {"alert": None, "message": "No alert warranted for current conditions", "signals": recent_signals}

    alert_dict = alert.model_dump()
    store["alerts"][alert.alert_id] = alert_dict

    audit_logger.log_alert(slope_id, {
        "alert_id": alert.alert_id,
        "level": alert.level.value,
        "risk_score": alert.risk_score,
        "signals": recent_signals,
    })

    return {"alert": alert_dict, "signals": recent_signals}


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, acknowledged_by: str = "operator"):
    if alert_id not in store["alerts"]:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert = store["alerts"][alert_id]
    alert["acknowledged"] = True
    alert["acknowledged_by"] = acknowledged_by
    alert["acknowledged_at"] = datetime.utcnow().isoformat()

    audit_logger.log_alert(alert["slope_id"], {
        "action": "acknowledge",
        "alert_id": alert_id,
        "acknowledged_by": acknowledged_by,
    })

    return {"alert": alert, "message": "Alert acknowledged"}
