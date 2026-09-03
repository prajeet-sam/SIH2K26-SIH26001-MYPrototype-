import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.schemas.models import ExposureRecord
from ml.susceptibility.model import SusceptibilityPredictor
from ml.dynamic.model import DynamicPredictor
from risk_engine.scorer import RiskEngine
from alert_engine.generator import AlertGenerator
from audit.logger import AuditLogger

store = {
    "slopes": {},
    "rainfall": {},
    "soil_moisture": {},
    "deformation": {},
    "exposures": {},
    "susceptibility_results": {},
    "hazard_results": {},
    "risk_results": {},
    "alerts": {},
    "audit_predictions": [],
    "audit_alerts": [],
    "audit_feedback": [],
    "last_train_metrics": {},
    "dynamic_train_metrics": {},
}

risk_engine = RiskEngine()
alert_generator = AlertGenerator()
audit_logger = AuditLogger(log_dir=str(Path(__file__).parent.parent / "audit"))
susceptibility_predictor: SusceptibilityPredictor | None = None
dynamic_predictor: DynamicPredictor | None = None
