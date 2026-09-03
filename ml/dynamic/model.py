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
from sklearn.model_selection import TimeSeriesSplit

from data.schemas.models import HazardOutput

HORIZONS = [6, 24, 72]

FEATURE_COLUMNS = [
    "rain_cum_1h",
    "rain_cum_3h",
    "rain_cum_6h",
    "rain_cum_24h",
    "rain_cum_72h",
    "rain_intensity_3h",
    "rain_intensity_6h",
    "rain_intensity_24h",
    "rain_roc_3h",
    "rain_roc_6h",
    "rain_roc_24h",
    "sm_current",
    "sm_roc_3h",
    "sm_roc_6h",
    "sm_roc_24h",
    "sm_mean_3h",
    "sm_mean_6h",
    "sm_mean_24h",
    "sm_std_3h",
    "sm_std_6h",
    "sm_std_24h",
    "sm_accel",
    "disp_current",
    "disp_rate_3h",
    "disp_rate_6h",
    "disp_rate_24h",
    "disp_accel_3h",
    "disp_accel_6h",
    "disp_mean_3h",
    "disp_mean_6h",
    "disp_mean_24h",
    "disp_max_3h",
    "disp_max_6h",
    "disp_max_24h",
    "disp_trend_24h",
    "awi_3d",
    "awi_7d",
    "awi_15d",
    "awi_30d",
    "susceptibility",
    "slope_angle",
    "elevation",
    "aspect",
    "curvature",
]


class DynamicPredictor:
    def __init__(
        self,
        horizons: list[int] | None = None,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        calibration_cv: int = 5,
        random_state: int = 42,
    ):
        self.horizons = horizons or HORIZONS
        self.calibration_cv = calibration_cv
        self.random_state = random_state
        self.models: dict[int, CalibratedClassifierCV] = {}
        self.feature_names: list[str] = list(FEATURE_COLUMNS)
        self._model_version = "dynamic-xgboost-v1"
        self._trained_at: Optional[datetime] = None
        self._n_estimators = n_estimators
        self._max_depth = max_depth
        self._learning_rate = learning_rate

    def _build_base_model(self) -> xgb.XGBClassifier:
        return xgb.XGBClassifier(
            n_estimators=self._n_estimators,
            max_depth=self._max_depth,
            learning_rate=self._learning_rate,
            subsample=0.85,
            colsample_bytree=0.85,
            colsample_bylevel=0.85,
            reg_alpha=0.3,
            reg_lambda=2.0,
            min_child_weight=3,
            gamma=0.1,
            objective="binary:logistic",
            eval_metric="auc",
            random_state=self.random_state,
            n_jobs=-1,
        )

    def train(
        self, X: pd.DataFrame, y: dict[int, pd.Series]
    ) -> dict[str, float]:
        self.feature_names = list(X.columns)
        results = {}

        for horizon in self.horizons:
            y_h = y[horizon]
            base_model = self._build_base_model()

            self.models[horizon] = CalibratedClassifierCV(
                base_model,
                method="isotonic",
                cv=self.calibration_cv,
            )
            self.models[horizon].fit(X, y_h)

            tscv = TimeSeriesSplit(n_splits=5)
            probas = np.zeros(len(y_h))
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train = y_h.iloc[train_idx]
                fold_model = self._build_base_model()
                fold_model.fit(X_train, y_train)
                probas[val_idx] = fold_model.predict_proba(X_val)[:, 1]

            from sklearn.metrics import roc_auc_score, f1_score

            valid_mask = ~np.isnan(y_h.values) & ~np.isnan(probas)
            auc = roc_auc_score(y_h.values[valid_mask], probas[valid_mask])
            preds = (probas[valid_mask] >= 0.5).astype(int)
            f1 = f1_score(y_h.values[valid_mask], preds)

            results[f"horizon_{horizon}h_auc"] = float(auc)
            results[f"horizon_{horizon}h_f1"] = float(f1)

        self._trained_at = datetime.utcnow()
        results["n_samples"] = len(X)
        return results

    def predict(
        self, X: pd.DataFrame, horizon: int
    ) -> list[HazardOutput]:
        if horizon not in self.models:
            raise ValueError(
                f"Horizon {horizon}h not in trained horizons: {list(self.models.keys())}"
            )

        X_aligned = X[self.feature_names]
        model = self.models[horizon]
        probas = model.predict_proba(X_aligned)[:, 1]
        confidence = np.abs(probas - 0.5) * 2

        outputs = []
        for i in range(len(X_aligned)):
            row = X_aligned.iloc[i]
            outputs.append(
                HazardOutput(
                    slope_id=str(row.get("slope_id", i)),
                    hazard_probability=float(probas[i]),
                    confidence=float(confidence[i]),
                    forecast_horizon_hours=horizon,
                    model_version=self._model_version,
                    computed_at=datetime.utcnow(),
                )
            )
        return outputs

    def predict_with_shap(
        self, X: pd.DataFrame, horizon: int
    ) -> list[dict]:
        if horizon not in self.models:
            raise ValueError(
                f"Horizon {horizon}h not in trained horizons: {list(self.models.keys())}"
            )

        X_aligned = X[self.feature_names]
        model = self.models[horizon]
        probas = model.predict_proba(X_aligned)[:, 1]

        booster = model.calibrated_classifiers_[0].estimator
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

            results.append(
                {
                    "slope_id": str(X_aligned.iloc[i].get("slope_id", i)),
                    "hazard_probability": float(probas[i]),
                    "forecast_horizon_hours": horizon,
                    "feature_contributions": sorted_contribs,
                    "model_version": self._model_version,
                }
            )
        return results

    def save(self, directory: str) -> Path:
        save_dir = Path(directory)
        save_dir.mkdir(parents=True, exist_ok=True)

        for horizon, model in self.models.items():
            model_path = save_dir / f"model_{horizon}h.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

        meta = {
            "horizons": self.horizons,
            "feature_names": self.feature_names,
            "model_version": self._model_version,
            "trained_at": self._trained_at.isoformat() if self._trained_at else None,
            "calibration_cv": self.calibration_cv,
            "n_estimators": self._n_estimators,
            "max_depth": self._max_depth,
            "learning_rate": self._learning_rate,
        }
        meta_path = save_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return save_dir

    @classmethod
    def load(cls, directory: str) -> "DynamicPredictor":
        load_dir = Path(directory)
        meta_path = load_dir / "metadata.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)

        predictor = cls(
            horizons=meta["horizons"],
            calibration_cv=meta["calibration_cv"],
            n_estimators=meta["n_estimators"],
            max_depth=meta["max_depth"],
            learning_rate=meta["learning_rate"],
        )
        predictor.feature_names = meta["feature_names"]
        predictor._model_version = meta["model_version"]
        predictor._trained_at = (
            datetime.fromisoformat(meta["trained_at"]) if meta["trained_at"] else None
        )

        for horizon in meta["horizons"]:
            model_path = load_dir / f"model_{horizon}h.pkl"
            with open(model_path, "rb") as f:
                predictor.models[horizon] = pickle.load(f)

        return predictor
