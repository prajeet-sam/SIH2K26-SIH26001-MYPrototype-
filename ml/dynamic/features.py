import numpy as np
import pandas as pd


def rolling_cumulative_rainfall(
    rainfall_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [1, 3, 6, 24, 72]
    result = {}
    for w in windows:
        result[f"rain_cum_{w}h"] = rainfall_series.rolling(w, min_periods=1).sum()
    return pd.DataFrame(result, index=rainfall_series.index)


def rolling_rainfall_intensity(
    rainfall_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [3, 6, 24]
    result = {}
    for w in windows:
        result[f"rain_intensity_{w}h"] = (
            rainfall_series.rolling(w, min_periods=1).sum() / w
        )
    return pd.DataFrame(result, index=rainfall_series.index)


def rainfall_rate_of_change(
    rainfall_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [3, 6, 24]
    result = {}
    for w in windows:
        result[f"rain_roc_{w}h"] = rainfall_series.diff(w) / w
    return pd.DataFrame(result, index=rainfall_series.index)


def soil_moisture_features(
    sm_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [3, 6, 24]
    result = {"sm_current": sm_series}
    result["sm_roc_3h"] = sm_series.diff(3)
    result["sm_roc_6h"] = sm_series.diff(6)
    result["sm_roc_24h"] = sm_series.diff(24)
    for w in windows:
        result[f"sm_mean_{w}h"] = sm_series.rolling(w, min_periods=1).mean()
        result[f"sm_std_{w}h"] = sm_series.rolling(w, min_periods=2).std()
    result["sm_accel"] = sm_series.diff(3).diff(3)
    return pd.DataFrame(result, index=sm_series.index)


def deformation_features(
    displacement_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [3, 6, 24]
    result = {"disp_current": displacement_series}
    result["disp_rate_3h"] = displacement_series.diff(3)
    result["disp_rate_6h"] = displacement_series.diff(6)
    result["disp_rate_24h"] = displacement_series.diff(24)
    result["disp_accel_3h"] = displacement_series.diff(3).diff(3)
    result["disp_accel_6h"] = displacement_series.diff(6).diff(6)
    for w in windows:
        result[f"disp_mean_{w}h"] = displacement_series.rolling(w, min_periods=1).mean()
        result[f"disp_max_{w}h"] = displacement_series.rolling(w, min_periods=1).max()
    result["disp_trend_24h"] = (
        displacement_series.rolling(24, min_periods=6).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
            raw=True,
        )
    )
    return pd.DataFrame(result, index=displacement_series.index)


def antecedent_wetness_index(
    rainfall_series: pd.Series,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    if windows is None:
        windows = [3, 7, 15, 30]
    result = {}
    for w in windows:
        result[f"awi_{w}d"] = rainfall_series.rolling(w * 24, min_periods=1).sum()
    return pd.DataFrame(result, index=rainfall_series.index)


def build_dynamic_feature_matrix(
    df: pd.DataFrame,
    susceptibility_col: str = "susceptibility_probability",
) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)

    if "rainfall_mm" in df.columns:
        features = pd.concat(
            [features, rolling_cumulative_rainfall(df["rainfall_mm"])], axis=1
        )
        features = pd.concat(
            [features, rolling_rainfall_intensity(df["rainfall_mm"])], axis=1
        )
        features = pd.concat(
            [features, rainfall_rate_of_change(df["rainfall_mm"])], axis=1
        )
        features = pd.concat(
            [features, antecedent_wetness_index(df["rainfall_mm"])], axis=1
        )

    if "volumetric_water_content" in df.columns:
        features = pd.concat(
            [features, soil_moisture_features(df["volumetric_water_content"])], axis=1
        )

    if "displacement_mm" in df.columns:
        features = pd.concat(
            [features, deformation_features(df["displacement_mm"])], axis=1
        )

    if susceptibility_col in df.columns:
        features["susceptibility"] = df[susceptibility_col]

    if "slope_angle" in df.columns:
        features["slope_angle"] = df["slope_angle"]
    if "elevation_m" in df.columns:
        features["elevation"] = df["elevation_m"]
    if "aspect_deg" in df.columns:
        features["aspect"] = df["aspect_deg"]
    if "curvature" in df.columns:
        features["curvature"] = df["curvature"]

    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.ffill().fillna(0)

    return features


def build_labels(
    df: pd.DataFrame,
    target_col: str = "landslide_occurred",
    horizons: list[int] | None = None,
) -> dict[str, pd.Series]:
    if horizons is None:
        horizons = [6, 24, 72]
    labels = {}
    for h in horizons:
        labels[f"target_{h}h"] = df[target_col].shift(-h).fillna(0).astype(int)
    return labels
