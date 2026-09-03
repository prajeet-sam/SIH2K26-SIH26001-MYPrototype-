from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    confusion_matrix,
)


@dataclass
class EvaluationMetrics:
    precision: float
    recall: float
    f1: float
    auc_roc: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    n_samples: int
    n_positive: int
    n_negative: int


@dataclass
class ReliabilityBin:
    bin_lower: float
    bin_upper: float
    mean_predicted: float
    fraction_positive: float
    count: int


@dataclass
class EvaluationReport:
    metrics: EvaluationMetrics
    reliability_bins: list[ReliabilityBin]
    holdout_type: str
    holdout_description: str


def compute_metrics(y_true: np.ndarray, y_pred_proba: np.ndarray, threshold: float = 0.5) -> EvaluationMetrics:
    y_pred = (y_pred_proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    return EvaluationMetrics(
        precision=precision_score(y_true, y_pred, zero_division=0),
        recall=recall_score(y_true, y_pred, zero_division=0),
        f1=f1_score(y_true, y_pred, zero_division=0),
        auc_roc=roc_auc_score(y_true, y_pred_proba) if len(np.unique(y_true)) > 1 else 0.0,
        true_positives=int(tp),
        false_positives=int(fp),
        true_negatives=int(tn),
        false_negatives=int(fn),
        n_samples=len(y_true),
        n_positive=int(y_true.sum()),
        n_negative=len(y_true) - int(y_true.sum()),
    )


def compute_reliability_data(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    n_bins: int = 10,
) -> list[ReliabilityBin]:
    bin_edges = np.linspace(0, 1, n_bins + 1)
    bins = []

    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]
        mask = (y_pred_proba >= lower) & (y_pred_proba < upper)
        if i == n_bins - 1:
            mask = (y_pred_proba >= lower) & (y_pred_proba <= upper)

        count = int(mask.sum())
        if count == 0:
            bins.append(
                ReliabilityBin(
                    bin_lower=float(lower),
                    bin_upper=float(upper),
                    mean_predicted=float((lower + upper) / 2),
                    fraction_positive=0.0,
                    count=0,
                )
            )
        else:
            bins.append(
                ReliabilityBin(
                    bin_lower=float(lower),
                    bin_upper=float(upper),
                    mean_predicted=float(y_pred_proba[mask].mean()),
                    fraction_positive=float(y_true[mask].mean()),
                    count=count,
                )
            )

    return bins


def temporal_holdout_evaluate(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    timestamps: pd.Series,
    cutoff_date: datetime,
) -> EvaluationReport:
    mask_future = timestamps >= cutoff_date

    y_true_holdout = y_true[mask_future]
    y_pred_holdout = y_pred_proba[mask_future]

    metrics = compute_metrics(y_true_holdout, y_pred_holdout)
    reliability = compute_reliability_data(y_true_holdout, y_pred_holdout)

    return EvaluationReport(
        metrics=metrics,
        reliability_bins=reliability,
        holdout_type="temporal",
        holdout_description=f"Samples with timestamp >= {cutoff_date.isoformat()}",
    )


def spatial_holdout_evaluate(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    holdout_slope_ids: set[str],
    slope_ids: pd.Series,
) -> EvaluationReport:
    mask_holdout = slope_ids.isin(holdout_slope_ids)

    y_true_holdout = y_true[mask_holdout]
    y_pred_holdout = y_pred_proba[mask_holdout]

    metrics = compute_metrics(y_true_holdout, y_pred_holdout)
    reliability = compute_reliability_data(y_true_holdout, y_pred_holdout)

    return EvaluationReport(
        metrics=metrics,
        reliability_bins=reliability,
        holdout_type="spatial",
        holdout_description=f"Held-out slope_ids: {len(holdout_slope_ids)} slopes",
    )


def spatial_block_holdout_evaluate(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    block_size_deg: float = 0.1,
) -> EvaluationReport:
    lat_blocks = np.floor(latitudes / block_size_deg).astype(int)
    lon_blocks = np.floor(longitudes / block_size_deg).astype(int)
    block_ids = lat_blocks * 1000 + lon_blocks

    unique_blocks = np.unique(block_ids)
    np.random.seed(42)
    holdout_blocks = set(np.random.choice(unique_blocks, size=max(1, len(unique_blocks) // 4), replace=False))

    mask_holdout = np.isin(block_ids, list(holdout_blocks))

    y_true_holdout = y_true[mask_holdout]
    y_pred_holdout = y_pred_proba[mask_holdout]

    metrics = compute_metrics(y_true_holdout, y_pred_holdout)
    reliability = compute_reliability_data(y_true_holdout, y_pred_holdout)

    return EvaluationReport(
        metrics=metrics,
        reliability_bins=reliability,
        holdout_type="spatial_block",
        holdout_description=f"Spatial block holdout with {len(holdout_blocks)} blocks of size {block_size_deg}deg",
    )


def cross_validation_evaluate(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    fold_ids: np.ndarray,
    n_folds: int = 5,
) -> list[EvaluationReport]:
    reports = []
    for fold in range(n_folds):
        mask = fold_ids == fold
        y_true_fold = y_true[mask]
        y_pred_fold = y_pred_proba[mask]

        metrics = compute_metrics(y_true_fold, y_pred_fold)
        reliability = compute_reliability_data(y_true_fold, y_pred_fold)

        reports.append(
            EvaluationReport(
                metrics=metrics,
                reliability_bins=reliability,
                holdout_type="cv_fold",
                holdout_description=f"Fold {fold + 1}/{n_folds}",
            )
        )
    return reports
