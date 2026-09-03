import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.state import store, audit_logger
from data.schemas.models import ProvenanceTag

router = APIRouter(prefix="/api/audit", tags=["audit"])


class FeedbackRequest(BaseModel):
    slope_id: str
    feedback_type: str
    rating: int | None = None
    comment: str | None = None
    submitted_by: str = "anonymous"


@router.get("/predictions")
def list_prediction_audit():
    records = list(store["audit_predictions"])
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return {"count": len(records), "records": records}


@router.get("/alerts")
def list_alert_audit():
    records = list(store["audit_alerts"])
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return {"count": len(records), "records": records}


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    if req.slope_id not in store["slopes"]:
        raise HTTPException(status_code=404, detail=f"Slope {req.slope_id} not found")

    record = audit_logger.log_feedback(req.slope_id, {
        "feedback_type": req.feedback_type,
        "rating": req.rating,
        "comment": req.comment,
        "submitted_by": req.submitted_by,
    })

    feedback_entry = {
        "record_id": record.record_id,
        "slope_id": req.slope_id,
        "timestamp": record.timestamp.isoformat(),
        "feedback_type": req.feedback_type,
        "rating": req.rating,
        "comment": req.comment,
        "submitted_by": req.submitted_by,
    }
    store["audit_feedback"].append(feedback_entry)

    return {"message": "Feedback recorded", "record_id": record.record_id}
