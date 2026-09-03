import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, r"C:\Users\HP\Desktop\SIH")

from data.schemas.models import (
    RiskOutput,
    ExposureRecord,
    ProvenanceTag,
)


ROAD_WEIGHTS = {"National": 1.0, "State": 0.85, "District": 0.6}


class RiskEngine:

    def compute_risk(
        self,
        slope_id: str,
        hazard_prob: float,
        exposure: Optional[ExposureRecord] = None,
        confidence: float = 0.0,
    ) -> RiskOutput:
        hazard_component = max(0.0, min(1.0, hazard_prob))

        exposure_weight, exposure_detail = self._compute_exposure_weight(exposure)
        exposure_component = exposure_weight

        raw_score = hazard_component * exposure_component * 100
        risk_score = int(max(0, min(100, round(raw_score))))

        priority_class = self._classify_priority(risk_score)

        uncertainty_notes = None
        if confidence < 0.5:
            uncertainty_notes = f"Low confidence ({confidence:.2f}); results may be unreliable."
        elif confidence < 0.7:
            uncertainty_notes = f"Moderate confidence ({confidence:.2f})."

        return RiskOutput(
            slope_id=slope_id,
            risk_score=risk_score,
            priority_class=priority_class,
            hazard_component=hazard_component,
            exposure_component=exposure_component,
            confidence=confidence,
            uncertainty_notes=uncertainty_notes,
            provenance=ProvenanceTag.MODEL_DERIVED,
            computed_at=datetime.utcnow(),
        )

    def _compute_exposure_weight(
        self, exposure: Optional[ExposureRecord]
    ) -> tuple[float, str]:
        if exposure is None:
            return 0.5, "No exposure data available; default weight 0.5 applied."

        weight = 0.2
        details = []

        pop = exposure.estimated_population or 0
        if pop > 10000:
            w = 1.0
        elif pop > 5000:
            w = 0.9
        elif pop > 1000:
            w = 0.7
        elif pop > 0:
            w = 0.5
        else:
            w = 0.2
        weight = max(weight, w)

        road_crit = exposure.road_criticality
        if road_crit in ROAD_WEIGHTS:
            w = ROAD_WEIGHTS[road_crit]
            weight = max(weight, w)

        if exposure.has_critical_infrastructure:
            weight = max(weight, 0.95)

        if exposure.has_hospital:
            weight = max(weight, 0.9)

        if exposure.has_school:
            weight = max(weight, 0.85)

        nearest_settlement = exposure.nearest_settlement_distance_m
        if nearest_settlement is not None:
            if nearest_settlement < 500:
                w = 0.95
            elif nearest_settlement < 1000:
                w = 0.8
            elif nearest_settlement < 2000:
                w = 0.6
            else:
                w = 0.3
            weight = max(weight, w)

        return weight, "; ".join(details) if details else "no significant exposure factors"

    @staticmethod
    def _classify_priority(score: int) -> str:
        if score <= 25:
            return "Low"
        if score <= 50:
            return "Moderate"
        if score <= 75:
            return "High"
        return "Critical"
