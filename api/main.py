import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.state import store, risk_engine, alert_generator, audit_logger
import api.state as state

from data.schemas.models import (
    SlopeUnit,
    DataQualityMetadata,
    DataQualityStatus,
    ProvenanceTag,
    CoverageMode,
    ExposureRecord,
    RiskOutput,
)
from data.ingestion.real_connectors import (
    build_real_slope_inventory,
    fetch_real_rainfall,
    fetch_real_forecast,
    load_nasa_landslide_catalog,
)
from data.simulated.generator import (
    generate_soil_moisture_series,
    generate_deformation_series,
)
from ml.susceptibility.model import SusceptibilityPredictor
from ml.susceptibility.features import (
    prepare_feature_matrix_from_dataframe,
    encode_lithology,
    encode_soil_type,
    encode_land_cover,
)
from ml.dynamic.model import DynamicPredictor
from ml.dynamic.features import build_dynamic_feature_matrix

app = FastAPI(
    title="Landslide Risk Monitoring System API",
    version="1.0.0",
    description="Demo/Simulation mode — generates synthetic pilot data on startup.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routers import slopes, predictions, alerts, quality, audit

app.include_router(slopes.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(quality.router)
app.include_router(audit.router)


def _generate_exposure(slope_data: dict) -> ExposureRecord:
    import random
    random.seed(hash(slope_data["slope_id"]) % (2**31))
    elev = slope_data.get("elevation_m", 1500)
    pop_base = max(0, int(5000 * math.exp(-elev / 2000))) if elev else 2000
    has_road = random.random() > 0.4
    has_settlement = random.random() > 0.3
    return ExposureRecord(
        slope_id=slope_data["slope_id"],
        nearest_road_distance_m=round(random.uniform(200, 15000), 1) if has_road else 99999.0,
        road_criticality=random.choice(["National", "State", "District"]) if has_road else "District",
        nearest_bridge_distance_m=round(random.uniform(500, 20000), 1),
        nearest_settlement_distance_m=round(random.uniform(200, 15000), 1) if has_settlement else 99999.0,
        estimated_population=random.randint(0, pop_base) if has_settlement else 0,
        has_school=random.random() > 0.85,
        has_hospital=random.random() > 0.95,
        has_critical_infrastructure=random.random() > 0.95,
        quality=DataQualityMetadata(
            timestamp=datetime.utcnow(),
            source="simulated_exposure",
            spatial_accuracy_m=50.0,
            sensor_health=DataQualityStatus.HEALTHY,
            provenance=ProvenanceTag.SIMULATED_DEMO,
        ),
    )


def _train_models():
    import random as _rand
    slope_dicts = list(store["slopes"].values())
    slope_df = pd.DataFrame(slope_dicts)

    slope_df["lithology_encoded"] = slope_df["lithology"].map(encode_lithology)
    slope_df["soil_type_encoded"] = slope_df["soil_type"].map(encode_soil_type)
    slope_df["land_cover_encoded"] = slope_df["land_cover"].map(encode_land_cover)

    if "has_landslide_label" in slope_df.columns:
        labels = slope_df["has_landslide_label"].values
    else:
        labels = np.random.binomial(1, 0.3, size=len(slope_df))

    # Augment: create additional samples from time-series statistics
    aug_rows = []
    aug_labels = []
    for _, row in slope_df.iterrows():
        slope_id = row["slope_id"]
        rain_records = store["rainfall"].get(slope_id, [])
        sm_records = store["soil_moisture"].get(slope_id, [])
        def_records = store["deformation"].get(slope_id, [])

        if len(rain_records) < 24:
            continue

        rain_vals = [r.rainfall_mm for r in rain_records]
        sm_vals = [s.volumetric_water_content for s in sm_records] if sm_records else [0.25] * len(rain_records)
        def_vals = [d.displacement_mm for d in def_records] if def_records else [0.5] * len(rain_records)

        base_label = row.get("has_landslide_label", 0)

        windows = [24, 48, 72, 120]
        for w in windows:
            if len(rain_vals) < w:
                continue
            rain_window = rain_vals[-w:]
            sm_window = sm_vals[-w:] if len(sm_vals) >= w else sm_vals
            def_window = def_vals[-w:] if len(def_vals) >= w else def_vals

            rain_cum = sum(rain_window)
            rain_max = max(rain_window)
            rain_mean = np.mean(rain_window)
            rain_std = np.std(rain_window)
            rain_intensity = rain_cum / w

            sm_current = sm_window[-1] if sm_window else 0.25
            sm_mean = np.mean(sm_window)
            sm_trend = (sm_window[-1] - sm_window[0]) if len(sm_window) > 1 else 0

            def_current = def_window[-1] if def_window else 0.5
            def_max = max(def_window)
            def_trend = (def_window[-1] - def_window[0]) if len(def_window) > 1 else 0
            def_accel = (def_window[-1] - 2 * def_window[len(def_window)//2] + def_window[0]) if len(def_window) > 2 else 0

            risk_signal = (
                0.3 * min(1.0, rain_cum / 200)
                + 0.2 * min(1.0, rain_max / 30)
                + 0.15 * min(1.0, max(0, sm_trend) * 10)
                + 0.15 * min(1.0, max(0, def_trend) * 5)
                + 0.1 * min(1.0, max(0, def_accel) * 3)
                + 0.1 * (row["slope_angle_deg"] / 55)
            )
            noisy_signal = risk_signal + _rand.gauss(0, 0.12)
            aug_label = 1 if (noisy_signal > 0.5 and base_label == 0) or base_label == 1 else 0
            if _rand.random() < 0.05:
                aug_label = 1 - aug_label

            aug_rows.append({
                "slope_angle": row["slope_angle_deg"],
                "elevation": row["elevation_m"],
                "aspect": row["aspect_deg"],
                "curvature": row["curvature"],
                "drainage_density": row.get("drainage_density", 1.5),
                "lithology_encoded": row["lithology_encoded"],
                "soil_type_encoded": row["soil_type_encoded"],
                "land_cover_encoded": row["land_cover_encoded"],
                "rain_cum": rain_cum,
                "rain_max": rain_max,
                "rain_mean": rain_mean,
                "rain_std": rain_std,
                "rain_intensity": rain_intensity,
                "sm_current": sm_current,
                "sm_mean": sm_mean,
                "sm_trend": sm_trend,
                "def_current": def_current,
                "def_max": def_max,
                "def_trend": def_trend,
                "def_accel": def_accel,
            })
            aug_labels.append(aug_label)

    X_orig = slope_df[["slope_angle_deg", "elevation_m", "aspect_deg", "curvature",
                        "drainage_density", "lithology_encoded", "soil_type_encoded", "land_cover_encoded"]].copy()
    X_orig.columns = ["slope_angle", "elevation", "aspect", "curvature",
                       "drainage_density", "lithology_encoded", "soil_type_encoded", "land_cover_encoded"]

    for col in ["rain_cum", "rain_max", "rain_mean", "rain_std", "rain_intensity",
                "sm_current", "sm_mean", "sm_trend", "def_current", "def_max", "def_trend", "def_accel"]:
        X_orig[col] = 0.0

    X_aug = pd.DataFrame(aug_rows)
    X_combined = pd.concat([X_orig, X_aug], ignore_index=True)
    y_combined = np.concatenate([labels, aug_labels])

    state.susceptibility_predictor = SusceptibilityPredictor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.03,
        calibration_cv=2,
        random_state=42,
    )
    y_series = pd.Series(y_combined)
    train_result = state.susceptibility_predictor.train(X_combined, y_series)
    store["last_train_metrics"] = train_result
    print(f"  Susceptibility: AUC={train_result['auc_cv']:.4f}, F1={train_result['f1_cv']:.4f}, samples={train_result['n_samples']}")

    # Dynamic model training
    combined_rows = []
    for slope_id, rain_records in store["rainfall"].items():
        if not rain_records:
            continue
        rain_df = pd.DataFrame([r.model_dump() for r in rain_records])
        sm_df = pd.DataFrame([s.model_dump() for s in store["soil_moisture"].get(slope_id, [])])
        def_df = pd.DataFrame([d.model_dump() for d in store["deformation"].get(slope_id, [])])

        if "timestamp" not in rain_df.columns or "rainfall_mm" not in rain_df.columns:
            continue

        merged = rain_df[["timestamp", "rainfall_mm"]].copy()
        if not sm_df.empty:
            merged = merged.merge(sm_df[["timestamp", "volumetric_water_content"]], on="timestamp", how="left")
        else:
            merged["volumetric_water_content"] = 0.25

        if not def_df.empty:
            merged = merged.merge(def_df[["timestamp", "displacement_mm"]], on="timestamp", how="left")
        else:
            merged["displacement_mm"] = 0.5

        slope_info = store["slopes"][slope_id]
        susc_prob = train_result.get("auc_cv", 0.5)
        merged["susceptibility_probability"] = susc_prob
        merged["slope_angle"] = slope_info["slope_angle_deg"]
        merged["elevation_m"] = slope_info["elevation_m"]
        merged["aspect_deg"] = slope_info["aspect_deg"]
        merged["curvature"] = slope_info["curvature"]

        last_row = merged.iloc[[-1]].copy()
        last_row["slope_id"] = slope_id
        combined_rows.append(last_row)

    if combined_rows:
        dynamic_df = pd.concat(combined_rows, ignore_index=True)
        dynamic_features = build_dynamic_feature_matrix(dynamic_df)

        slope_labels_map = {s["slope_id"]: s.get("has_landslide_label", 0) for s in slope_dicts}

        def _make_dynamic_labels(slope_id):
            base = slope_labels_map.get(slope_id, 0)
            rain_records = store["rainfall"].get(slope_id, [])
            recent_rain = sum(r.rainfall_mm for r in rain_records[-6:]) if len(rain_records) >= 6 else 0
            trigger = 1 if recent_rain > 25 else 0
            return {
                6: min(1, base | trigger),
                24: min(1, base | trigger),
                72: min(1, base),
            }

        dynamic_labels = {6: [], 24: [], 72: []}
        included_slopes = set(dynamic_df["slope_id"].tolist()) if "slope_id" in dynamic_df.columns else set()
        for slope_id in store["rainfall"]:
            if slope_id not in included_slopes:
                continue
            lbls = _make_dynamic_labels(slope_id)
            for h in [6, 24, 72]:
                dynamic_labels[h].append(int(lbls[h]))

        for h in [6, 24, 72]:
            dynamic_labels[h] = pd.Series(dynamic_labels[h], dtype=int)

        state.dynamic_predictor = DynamicPredictor(
            horizons=[6, 24, 72],
            n_estimators=300,
            max_depth=6,
            learning_rate=0.03,
            calibration_cv=2,
            random_state=42,
        )

        can_train_dynamic = True
        for h in [6, 24, 72]:
            if len(dynamic_labels[h].unique()) < 2:
                print(f"  Dynamic {h}h: only one class ({dynamic_labels[h].unique()[0]}), skipping calibration")
                can_train_dynamic = False
                break

        if can_train_dynamic:
            try:
                dyn_metrics = state.dynamic_predictor.train(dynamic_features, dynamic_labels)
                store["dynamic_train_metrics"] = dyn_metrics
                for k, v in dyn_metrics.items():
                    if isinstance(v, float):
                        print(f"  Dynamic {k}: {v:.4f}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"  Dynamic model training failed: {e}")
                state.dynamic_predictor = None
                store["dynamic_train_metrics"] = {}
        else:
            state.dynamic_predictor = None
            store["dynamic_train_metrics"] = {}


@app.on_event("startup")
def startup_event():
    import random
    random.seed(42)
    np.random.seed(42)

    print("LANDSLIDE RISK MONITORING SYSTEM - STARTUP")

    real_slopes = build_real_slope_inventory()
    print(f"Loaded {len(real_slopes)} real NER slope locations")

    nasa_events = load_nasa_landslide_catalog()
    print(f"Found {len(nasa_events)} historical landslides in NER")

    # Assign labels based on proximity to real landslide events + terrain risk
    for slope in real_slopes:
        min_dist = float("inf")
        for evt in nasa_events:
            dist = math.sqrt(
                (slope["latitude"] - evt["latitude"]) ** 2 +
                (slope["longitude"] - evt["longitude"]) ** 2
            )
            min_dist = min(min_dist, dist)

        proximity_factor = max(0, 1.0 - min_dist / 0.3)
        elevation_factor = min(1.0, slope["elevation_m"] / 2500)
        slope_factor = slope["slope_angle_deg"] / 55.0
        risk_score = 0.4 * proximity_factor + 0.3 * slope_factor + 0.3 * elevation_factor
        has_event = risk_score > 0.65
        slope["has_landslide_label"] = 1 if has_event else 0
        slope["label_confidence"] = round(max(0.3, min(0.95, risk_score)), 2)

    n_positive = sum(s["has_landslide_label"] for s in real_slopes)
    print(f"Labels: {n_positive} positive / {len(real_slopes) - n_positive} negative")

    # Fetch real rainfall data from Open-Meteo (concurrent)
    start_time = datetime.utcnow()

    def _fetch_slope_data(slope):
        sid = slope["slope_id"]
        real_rain = fetch_real_rainfall(slope["latitude"], slope["longitude"], days_back=14)
        for r in real_rain:
            r.slope_id = sid
        forecast_rain = fetch_real_forecast(slope["latitude"], slope["longitude"], days_ahead=3)
        for r in forecast_rain:
            r.slope_id = sid
        return sid, real_rain, forecast_rain

    rain_results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_slope_data, s): s for s in real_slopes}
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            try:
                sid, real_rain, forecast_rain = future.result(timeout=20)
                rain_results[sid] = (real_rain, forecast_rain)
            except Exception as e:
                slope = futures[future]
                sid = slope["slope_id"]
                rain_results[sid] = ([], [])

    for slope in real_slopes:
        sid = slope["slope_id"]
        real_rain, forecast_rain = rain_results.get(sid, ([], []))
        store["rainfall"][sid] = real_rain

        sm_records = generate_soil_moisture_series(
            sid, start_time, hours=max(len(real_rain), 168),
            rainfall_records=real_rain,
        )
        store["soil_moisture"][sid] = sm_records
        store["deformation"][sid] = generate_deformation_series(
            sid, start_time, hours=max(len(real_rain), 168),
            slope_angle_deg=slope["slope_angle_deg"],
            rainfall_records=real_rain,
            soil_moisture_records=sm_records,
        )

        quality = DataQualityMetadata(
            timestamp=start_time,
            source="real-inventory",
            spatial_accuracy_m=10.0,
            sensor_health=DataQualityStatus.HEALTHY,
            provenance=ProvenanceTag.OBSERVED,
        )
        slope_unit = SlopeUnit(
            slope_id=sid,
            latitude=slope["latitude"],
            longitude=slope["longitude"],
            elevation_m=slope["elevation_m"],
            slope_angle_deg=slope["slope_angle_deg"],
            aspect_deg=slope["aspect_deg"],
            curvature=slope["curvature"],
            area_sq_km=slope["area_sq_km"],
            district=slope["district"],
            state=slope["state"],
            coverage_mode=CoverageMode.MODELED_ONLY,
            quality=quality,
        )
        store["slopes"][sid] = slope_unit.model_dump()
        store["slopes"][sid]["lithology"] = slope["lithology"]
        store["slopes"][sid]["soil_type"] = slope["soil_type"]
        store["slopes"][sid]["land_cover"] = slope["land_cover"]
        store["slopes"][sid]["drainage_density"] = slope["drainage_density"]
        store["slopes"][sid]["has_landslide_label"] = slope["has_landslide_label"]
        store["slopes"][sid]["label_confidence"] = slope["label_confidence"]
        store["slopes"][sid]["name"] = slope.get("name", sid)
        store["slopes"][sid]["clay_pct"] = slope.get("clay_pct")
        store["slopes"][sid]["sand_pct"] = slope.get("sand_pct")
        store["slopes"][sid]["organic_carbon"] = slope.get("organic_carbon")
        store["slopes"][sid]["soil_ph"] = slope.get("soil_ph")

        store["exposures"][sid] = _generate_exposure(slope)

    print(f"Loaded {len(store['slopes'])} slopes with real data")

    # Train models
    print("Training ML models...")
    _train_models()

    # Compute risk scores
    from api.routers.predictions import _get_slope_features, _get_dynamic_features
    from ml.susceptibility.features import prepare_feature_matrix_from_dataframe

    for slope_id in list(store["slopes"].keys()):
        try:
            if state.susceptibility_predictor is not None:
                X = _get_slope_features(slope_id)
                results = state.susceptibility_predictor.predict_with_shap(X, slope_ids=[slope_id])
                result = results[0] if results else {}
                susc_prob = result.get("susceptibility_probability", 0.5)
                store["susceptibility_results"][slope_id] = {
                    "slope_id": slope_id,
                    "susceptibility_probability": susc_prob,
                    "confidence": abs(susc_prob - 0.5) * 2,
                    "model_version": result.get("model_version", "unknown"),
                    "feature_contributions": result.get("feature_contributions", {}),
                    "computed_at": datetime.utcnow().isoformat(),
                }
            else:
                susc_prob = 0.5

            hazard_prob = susc_prob
            if state.dynamic_predictor is not None and state.dynamic_predictor.models:
                try:
                    X_dyn = _get_dynamic_features(slope_id)
                    dyn_results = state.dynamic_predictor.predict_with_shap(X_dyn, horizon=24)
                    dyn_result = dyn_results[0] if dyn_results else {}
                    dyn_hazard = dyn_result.get("hazard_probability", susc_prob)
                    dyn_confidence = abs(dyn_hazard - 0.5) * 2
                    susc_confidence = abs(susc_prob - 0.5) * 2
                    if dyn_confidence > susc_confidence:
                        hazard_prob = dyn_hazard
                    store["hazard_results"][slope_id] = {
                        "slope_id": slope_id,
                        "hazard_probability": hazard_prob,
                        "confidence": abs(hazard_prob - 0.5) * 2,
                        "forecast_horizon_hours": 24,
                        "computed_at": datetime.utcnow().isoformat(),
                    }
                except Exception:
                    pass

            exposure = store["exposures"].get(slope_id)
            risk_output = risk_engine.compute_risk(slope_id, hazard_prob, exposure, abs(hazard_prob - 0.5) * 2)
            store["risk_results"][slope_id] = risk_output.model_dump()

        except Exception as e:
            print(f"  Risk computation failed for {slope_id}: {e}")

    # Generate initial alerts
    from api.routers.alerts import _extract_recent_signals
    for slope_id in list(store["slopes"].keys()):
        risk_data = store["risk_results"].get(slope_id)
        if risk_data is None:
            continue
        risk_output = RiskOutput(
            slope_id=risk_data["slope_id"],
            risk_score=risk_data["risk_score"],
            priority_class=risk_data["priority_class"],
            hazard_component=risk_data["hazard_component"],
            exposure_component=risk_data["exposure_component"],
            confidence=risk_data["confidence"],
            uncertainty_notes=risk_data.get("uncertainty_notes"),
            provenance=ProvenanceTag.MODEL_DERIVED,
            computed_at=datetime.utcnow(),
        )
        recent_signals = _extract_recent_signals(slope_id)
        alert = alert_generator.evaluate(slope_id, risk_output, recent_signals)
        if alert is not None:
            store["alerts"][alert.alert_id] = alert.model_dump()

    print(f"Startup complete: {len(store['slopes'])} slopes, "
          f"{len(store['risk_results'])} risk scores, "
          f"{len(store['alerts'])} alerts")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "real-data",
        "slopes_loaded": len(store["slopes"]),
        "models_trained": state.susceptibility_predictor is not None,
        "historical_events": len(load_nasa_landslide_catalog()),
    }


@app.get("/api/metrics")
def get_metrics():
    train_metrics = store.get("last_train_metrics", {})
    dynamic_metrics = store.get("dynamic_train_metrics", {})

    slope_dicts = list(store["slopes"].values())
    labels = [s.get("has_landslide_label", 0) for s in slope_dicts]
    n_positive = sum(labels)
    n_negative = len(labels) - n_positive

    return {
        "susceptibility_model": {
            "train_metrics": train_metrics,
            "n_samples": len(labels),
            "n_positive": n_positive,
            "n_negative": n_negative,
            "class_balance": round(n_positive / max(1, len(labels)), 3),
        },
        "dynamic_model": {
            "train_metrics": dynamic_metrics,
        },
        "total_predictions": len(store["risk_results"]),
        "total_alerts": len(store["alerts"]),
    }
