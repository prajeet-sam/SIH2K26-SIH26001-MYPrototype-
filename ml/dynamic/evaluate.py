from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
    confusion_matrix,
)

from ml.dynamic.features import build_dynamic_feature_matrix, build_labels


@dataclass
class HorizonMetrics:
    horizon_hours: int
    precision: float
    recall: float
    f1: float
    auc_roc: float
    average_precision: float
    support: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    prevalence: float


@dataclass
class EvaluationReport:
    horizons: list[HorizonMetrics]
    overall_metrics: dict[str, float] = field(default_factory=dict)


def temporal_train_test_split(
    df: pd.DataFrame,
    test_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(df)
    split_idx = int(n * (1 - test_fraction))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def evaluate_horizon(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    horizon_hours: int,
    threshold: float = 0.5,
) -> HorizonMetrics:
    valid_mask = ~np.isnan(y_true) & ~np.isnan(y_pred_proba)
    y_true = y_true[valid_mask]
    y_pred_proba = y_pred_proba[valid_mask]

    y_pred = (y_pred_proba >= threshold).astype(int)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    if len(np.unique(y_true)) < 2:
        auc_roc = 0.0
        avg_precision = 0.0
    else:
        auc_roc = roc_auc_score(y_true, y_pred_proba)
        avg_precision = average_precision_score(y_true, y_pred_proba)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    prevalence = float(np.mean(y_true)) if len(y_true) > 0 else 0.0

    return HorizonMetrics(
        horizon_hours=horizon_hours,
        precision=float(precision),
        recall=float(recall),
        f1=float(f1),
        auc_roc=float(auc_roc),
        average_precision=float(avg_precision),
        support=len(y_true),
        true_positives=int(tp),
        false_positives=int(fp),
        true_negatives=int(tn),
        false_negatives=int(fn),
        prevalence=prevalence,
    )


def evaluate_temporal_holdout(
    predictor,
    df: pd.DataFrame,
    test_fraction: float = 0.2,
    susceptibility_col: str = "susceptibility_probability",
    target_col: str = "landslide_occurred",
) -> EvaluationReport:
    train_df, test_df = temporal_train_test_split(df, test_fraction)

    X_train = build_dynamic_feature_matrix(train_df, susceptibility_col)
    labels_train = build_labels(train_df, target_col, predictor.horizons)
    y_train = {h: labels_train[f"target_{h}h"] for h in predictor.horizons}

    predictor.train(X_train, y_train)

    X_test = build_dynamic_feature_matrix(test_df, susceptibility_col)
    labels_test = build_labels(test_df, target_col, predictor.horizons)

    horizon_metrics = []
    for horizon in predictor.horizons:
        y_test = labels_test[f"target_{horizon}h"].values
        outputs = predictor.predict(X_test, horizon)
        y_pred_proba = np.array([o.hazard_probability for o in outputs])

        metrics = evaluate_horizon(y_test, y_pred_proba, horizon)
        horizon_metrics.append(metrics)

    overall = {}
    if horizon_metrics:
        overall["mean_f1"] = float(np.mean([m.f1 for m in horizon_metrics]))
        overall["mean_auc_roc"] = float(np.mean([m.auc_roc for m in horizon_metrics]))
        overall["mean_precision"] = float(
            np.mean([m.precision for m in horizon_metrics])
        )
        overall["mean_recall"] = float(np.mean([m.recall for m in horizon_metrics]))
        overall["best_horizon_f1"] = float(max(m.f1 for m in horizon_metrics))
        overall["worst_horizon_f1"] = float(min(m.f1 for m in horizon_metrics))

    return EvaluationReport(horizons=horizon_metrics, overall_metrics=overall)


def print_evaluation_report(report: EvaluationReport) -> None:
    print("DYNAMIC PREDICTION MODEL - TEMPORAL HOLD-OUT EVALUATION")

    for m in report.horizons:
        print(f"\n--- Horizon: {m.horizon_hours}h ---")
        print(f"  Precision:        {m.precision:.4f}")
        print(f"  Recall:           {m.recall:.4f}")
        print(f"  F1 Score:         {m.f1:.4f}")
        print(f"  AUC-ROC:          {m.auc_roc:.4f}")
        print(f"  Avg Precision:    {m.average_precision:.4f}")
        print(f"  Prevalence:       {m.prevalence:.4f}")
        print(f"  Support:          {m.support}")
        print(
            f"  Confusion: TP={m.true_positives} FP={m.false_positives} "
            f"TN={m.true_negatives} FN={m.false_negatives}"
        )

    if report.overall_metrics:
        print("\n--- Overall ---")
        for k, v in report.overall_metrics.items():
            print(f"  {k}: {v:.4f}")


def compute_optimal_thresholds(
    predictor,
    X_val: pd.DataFrame,
    y_val: dict[int, pd.Series],
) -> dict[int, float]:
    thresholds = {}
    for horizon in predictor.horizons:
        y_true = y_val[horizon].values
        outputs = predictor.predict(X_val, horizon)
        y_pred_proba = np.array([o.hazard_probability for o in outputs])

        valid_mask = ~np.isnan(y_true) & ~np.isnan(y_pred_proba)
        y_true = y_true[valid_mask]
        y_pred_proba = y_pred_proba[valid_mask]

        if len(np.unique(y_true)) < 2:
            thresholds[horizon] = 0.5
            continue

        precisions, recalls, thresh = precision_recall_curve(y_true, y_pred_proba)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
        best_idx = np.argmax(f1_scores)
        thresholds[horizon] = float(thresh[best_idx]) if best_idx < len(thresh) else 0.5

    return thresholds
