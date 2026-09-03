import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, r"C:\Users\HP\Desktop\SIH")

from data.schemas.models import (
    CandidateAlert,
    AlertLevel,
    RiskOutput,
    ProvenanceTag,
)


class AlertGenerator:

    def evaluate(
        self,
        slope_id: str,
        risk_output: RiskOutput,
        recent_signals: Optional[dict] = None,
    ) -> Optional[CandidateAlert]:
        signals = recent_signals or {}
        risk_score = risk_output.risk_score
        confidence = risk_output.confidence
        hazard_prob = risk_output.hazard_component

        soil_moisture_rising = signals.get("soil_moisture_rising", False)
        rainfall_elevated = signals.get("rainfall_elevated", False)
        deformation_detected = signals.get("deformation_detected", False)
        multiple_signals = sum(
            [soil_moisture_rising, rainfall_elevated, deformation_detected]
        )

        evidence = []
        if soil_moisture_rising:
            evidence.append("Soil moisture is rising")
        if rainfall_elevated:
            evidence.append("Elevated rainfall detected")
        if deformation_detected:
            evidence.append("Ground deformation detected")
        evidence.append(f"Risk score: {risk_score}/100")
        evidence.append(f"Hazard probability: {hazard_prob:.2f}")
        evidence.append(f"Confidence: {confidence:.2f}")

        level, action = self._determine_level(
            risk_score, confidence, hazard_prob,
            soil_moisture_rising, rainfall_elevated,
            deformation_detected, multiple_signals,
        )

        if level is None:
            return None

        return CandidateAlert(
            alert_id=f"CAND-{slope_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            slope_id=slope_id,
            level=level,
            hazard_probability=hazard_prob,
            risk_score=risk_score,
            confidence=confidence,
            contributing_evidence=evidence,
            recommended_action=action,
            generated_at=datetime.utcnow(),
            provenance=ProvenanceTag.MODEL_DERIVED,
        )

    def _determine_level(
        self,
        risk_score: int,
        confidence: float,
        hazard_prob: float,
        soil_moisture_rising: bool,
        rainfall_elevated: bool,
        deformation_detected: bool,
        multiple_signals: int,
    ) -> tuple[Optional[AlertLevel], Optional[str]]:
        if risk_score >= 70 and confidence > 0.6 and hazard_prob > 0.5:
            action = (
                "Evacuate exposed populations immediately. Close affected roads. "
                "Deploy emergency response teams. Continuous monitoring required."
            )
            return AlertLevel.CRITICAL, action

        if (
            risk_score >= 50
            and confidence > 0.5
            and hazard_prob > 0.3
            and multiple_signals >= 1
        ):
            action = (
                "Prepare for possible evacuation. Issue public warning. "
                "Increase monitoring frequency. Pre-position emergency resources."
            )
            return AlertLevel.WARNING, action

        if (
            risk_score >= 30
            and confidence > 0.3
        ):
            action = (
                "Monitor slope conditions closely. Review evacuation plans. "
                "Notify local authorities of elevated risk."
            )
            return AlertLevel.WATCH, action

        return None, None
