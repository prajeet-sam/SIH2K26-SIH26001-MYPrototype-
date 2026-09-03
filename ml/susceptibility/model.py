import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

from data.schemas.models import SusceptibilityOutput

FEATURE_COLUMNS = [
    "slope_angle",
    "elevation",
    "aspect",
    "curvature",
    "drainage_density",
    "lithology_encoded",
    "soil_type_encoded",
    "land_cover_encoded",
]


class SusceptibilityPredictor:
    def __init__(
        self,
        model_type: str = "xgboost",
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        calibration_cv: int = 5,
        random_state: int = 42,
    ):
        self.model_type = model_type
        self.calibration_cv = calibration_cv
        self.random_state = random_state
        self.calibrated_model: Optional[CalibratedClassifierCV] = None
        self.feature_names = FEATURE_COLUMNS
        self._model_version = f"susceptibility-{model_type}-v1"
        self._trained_at: Optional[datetime] = None

        if model_type == "xgboost":
            self.base_model = xgb.XGBClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.85,
                colsample_bytree=0.85,
                colsample_bylevel=0.85,
                reg_alpha=0.3,
                reg_lambda=2.0,
                min_child_weight=3,
                gamma=0.1,
                objective="binary:logistic",
                eval_metric="auc",
                random_state=random_state,
                n_jobs=-1,
            )
        elif model_type == "lightgbm":
            import lightgbm as lgb

            self.base_model = lgb.LGBMClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                objective="binary",
                random_state=random_state,
                verbose=-1,
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        self.feature_names = list(X.columns)

        self.calibrated_model = CalibratedClassifierCV(
            self.base_model,
            method="isotonic",
            cv=self.calibration_cv,
        )
        self.calibrated_model.fit(X, y)
        self._trained_at = datetime.utcnow()

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        probabilities = np.zeros(len(y))
        for train_idx, val_idx in cv.split(X, y):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train = y.iloc[train_idx]
            fold_model = self.base_model.__class__(
                **self.base_model.get_params()
            )
            fold_model.fit(X_train, y_train)
            probabilities[val_idx] = fold_model.predict_proba(X_val)[:, 1]

        from sklearn.metrics import roc_auc_score, f1_score

        auc = roc_auc_score(y, probabilities)
        preds = (probabilities >= 0.5).astype(int)
        f1 = f1_score(y, preds)

        return {"auc_cv": auc, "f1_cv": f1, "n_samples": len(y)}

    def predict(self, X: pd.DataFrame, slope_ids: list[str] | None = None) -> list[SusceptibilityOutput]:
        X_aligned = X[self.feature_names]
        probas = self.calibrated_model.predict_proba(X_aligned)[:, 1]
        confidence = np.abs(probas - 0.5) * 2

        outputs = []
        for i in range(len(X_aligned)):
            sid = slope_ids[i] if slope_ids and i < len(slope_ids) else str(i)
            outputs.append(
                SusceptibilityOutput(
                    slope_id=sid,
                    susceptibility_probability=float(probas[i]),
                    confidence=float(confidence[i]),
                    model_version=self._model_version,
                    computed_at=datetime.utcnow(),
                )
            )
        return outputs

    def predict_with_shap(self, X: pd.DataFrame, slope_ids: list[str] | None = None) -> list[dict]:
        X_aligned = X[self.feature_names]
        probas = self.calibrated_model.predict_proba(X_aligned)[:, 1]

        booster = self.calibrated_model.calibrated_classifiers_[0].estimator
        explainer = shap.TreeExplainer(booster)
        shap_values = explainer.shap_values(X_aligned)

        results = []
        for i in range(len(X_aligned)):
            contribs = {}
            for j, feat in enumerate(self.feature_names):
                contribs[feat] = float(shap_values[i][j])

            sorted_contribs = dict(
                sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)
            )

            sid = slope_ids[i] if slope_ids and i < len(slope_ids) else str(i)
            results.append(
                {
                    "slope_id": sid,
                    "susceptibility_probability": float(probas[i]),
                    "feature_contributions": sorted_contribs,
                    "model_version": self._model_version,
                }
            )
        return results

    def save(self, directory: str) -> Path:
        save_dir = Path(directory)
        save_dir.mkdir(parents=True, exist_ok=True)

        model_path = save_dir / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(self.calibrated_model, f)

        meta = {
            "model_type": self.model_type,
            "model_version": self._model_version,
            "feature_names": self.feature_names,
            "trained_at": self._trained_at.isoformat() if self._trained_at else None,
            "calibration_cv": self.calibration_cv,
        }
        meta_path = save_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return save_dir

    @classmethod
    def load(cls, directory: str) -> "SusceptibilityPredictor":
        load_dir = Path(directory)
        meta_path = load_dir / "metadata.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)

        predictor = cls(
            model_type=meta["model_type"],
            calibration_cv=meta["calibration_cv"],
        )
        predictor.feature_names = meta["feature_names"]
        predictor._model_version = meta["model_version"]
        predictor._trained_at = (
            datetime.fromisoformat(meta["trained_at"]) if meta["trained_at"] else None
        )

        model_path = load_dir / "model.pkl"
        with open(model_path, "rb") as f:
            predictor.calibrated_model = pickle.load(f)

        return predictor
