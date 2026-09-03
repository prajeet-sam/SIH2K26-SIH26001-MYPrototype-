import json
import os
import sys
from datetime import datetime
from typing import Any
from uuid import uuid4

sys.path.insert(0, r"C:\Users\HP\Desktop\SIH")

from data.schemas.models import (
    AuditRecord,
    ProvenanceTag,
)


class AuditLogger:

    def __init__(self, log_dir: str = r"C:\Users\HP\Desktop\SIH\audit"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def log_prediction(
        self,
        slope_id: str,
        data: dict[str, Any],
        provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED,
    ) -> AuditRecord:
        return self._write("prediction", slope_id, data, provenance)

    def log_alert(
        self,
        slope_id: str,
        data: dict[str, Any],
        provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED,
    ) -> AuditRecord:
        return self._write("alert", slope_id, data, provenance)

    def log_feedback(
        self,
        slope_id: str,
        data: dict[str, Any],
        provenance: ProvenanceTag = ProvenanceTag.MODEL_DERIVED,
    ) -> AuditRecord:
        return self._write("feedback", slope_id, data, provenance)

    def _write(
        self,
        record_type: str,
        slope_id: str,
        data: dict[str, Any],
        provenance: ProvenanceTag,
    ) -> AuditRecord:
        record = AuditRecord(
            record_id=f"audit-{uuid4().hex[:12]}",
            record_type=record_type,
            slope_id=slope_id,
            timestamp=datetime.utcnow(),
            data=data,
            provenance=provenance,
        )

        filename = f"{record_type}_trail.jsonl"
        filepath = os.path.join(self.log_dir, filename)

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        return record
